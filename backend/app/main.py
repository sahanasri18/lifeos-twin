import os

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

from app.models.scenario import ScenarioRequest, ScenarioResult
from app.models.knowledge import KnowledgeQuery, KnowledgeResponse, KnowledgeIngest, KnowledgeIngestResponse
from app.models.agents import InvestigationRequest, InvestigationResponse
from app.services.knowledge_service import answer_question
from app.knowledge.document_store import store
from app.knowledge.retriever import retriever
from app.services.agent_workflow import investigate
from app.services.city_data import CITY_NAME, DATA_LABEL, DISTRICTS
from app.services.simulation import simulate_scenario
from app.services.local_llm import llm_settings
from app.models.scenario_history import ScenarioSaveRequest, ScenarioCompareRequest
from app.models.scenario_explorer import WhatIfRequest
from app.models.forecast import ForecastRequest
from app.models.external_data import WeatherRequest
from app.services.external_data import source_catalog, fetch_current_weather
from app.services.forecast_service import forecast_scenario
from app.services.scenario_explorer import explore_scenarios
from app.services.scenario_store import scenario_store
from app.services.report_service import build_scenario_report, build_comparison_report, build_investigation_report
from app.models.workspace import RegisterRequest, LoginRequest, WorkspaceScenarioRequest, WorkspaceDocumentRequest
from app.services.workspace_service import workspace

app = FastAPI(
    title="LifeOS Twin API",
    description="Synthetic-city digital twin and transparent scenario simulation prototype.",
    version="0.1.0",
)

# Set LIFEOS_CORS_ORIGINS to a comma-separated allowlist for hosted deployments.
# The wildcard default is convenient for local development; credentials stay disabled.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("LIFEOS_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

MAX_REQUEST_BYTES = 1_000_000
_bearer = HTTPBearer(auto_error=False)


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="A valid bearer token is required.", headers={"WWW-Authenticate": "Bearer"})
    user = workspace.verify_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Token is invalid or expired.", headers={"WWW-Authenticate": "Bearer"})
    return user


@app.get("/auth/status")
def auth_status() -> dict:
    return {"enabled": True, "token_lifetime_seconds": 43200, "development_secret_warning": workspace.uses_development_secret, "note": "Set LIFEOS_AUTH_SECRET to a long random value before deployment."}


@app.post("/auth/register", status_code=201)
def register_account(request: RegisterRequest) -> dict:
    try:
        user = workspace.register(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 422, detail=str(exc)) from exc
    return {"user": user, "token_type": "bearer", "access_token": workspace.issue_token(user), "expires_in": 43200}


@app.post("/auth/login")
def login_account(request: LoginRequest) -> dict:
    user = workspace.authenticate(request.email, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.", headers={"WWW-Authenticate": "Bearer"})
    return {"user": user, "token_type": "bearer", "access_token": workspace.issue_token(user), "expires_in": 43200}


@app.get("/auth/me")
def current_account(user: dict = Depends(require_user)) -> dict:
    return {"user": user}


@app.post("/workspace/scenarios", status_code=201)
def create_workspace_scenario(request: WorkspaceScenarioRequest, user: dict = Depends(require_user)) -> dict:
    try:
        return workspace.create_scenario(user["id"], request.name, request.request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/workspace/scenarios")
def list_workspace_scenarios(user: dict = Depends(require_user)) -> dict:
    items = workspace.list_scenarios(user["id"])
    return {"scenarios": items, "count": len(items)}


@app.post("/workspace/scenarios/compare/report.pdf")
def download_workspace_comparison_report(request: ScenarioCompareRequest, user: dict = Depends(require_user)) -> Response:
    try:
        records = workspace.get_scenarios(user["id"], request.scenario_ids)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    from datetime import datetime, timezone
    from app.models.scenario_history import SavedScenario
    scenarios = [SavedScenario(
        id=record["id"], name=record["name"],
        created_at=datetime.fromtimestamp(record["created_at"], tz=timezone.utc).isoformat(),
        request=record["request"], result=record["result"],
    ) for record in records]
    pdf = build_comparison_report(scenarios)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="lifeos-private-scenario-comparison.pdf"'
    })


@app.get("/workspace/scenarios/{scenario_id}/report.pdf")
def download_workspace_scenario_report(scenario_id: str, user: dict = Depends(require_user)) -> Response:
    record = workspace.get_scenario(user["id"], scenario_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workspace scenario not found.")
    from datetime import datetime, timezone
    from app.models.scenario_history import SavedScenario
    scenario = SavedScenario(
        id=record["id"], name=record["name"],
        created_at=datetime.fromtimestamp(record["created_at"], tz=timezone.utc).isoformat(),
        request=record["request"], result=record["result"],
    )
    pdf = build_scenario_report(scenario)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="lifeos-private-scenario-{scenario_id[:8]}.pdf"'
    })


@app.delete("/workspace/scenarios/{scenario_id}")
def delete_workspace_scenario(scenario_id: str, user: dict = Depends(require_user)) -> dict:
    if not workspace.delete_scenario(user["id"], scenario_id):
        raise HTTPException(status_code=404, detail="Workspace scenario not found.")
    return {"status": "deleted", "id": scenario_id}


@app.post("/workspace/documents", status_code=201)
def create_workspace_document(request: WorkspaceDocumentRequest, user: dict = Depends(require_user)) -> dict:
    try:
        return workspace.create_document(user["id"], request.title, request.domain, request.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/workspace/documents")
def list_workspace_documents(user: dict = Depends(require_user)) -> dict:
    items = workspace.list_documents(user["id"])
    return {"documents": items, "count": len(items)}


@app.post("/workspace/knowledge/query")
def query_private_knowledge(request: KnowledgeQuery, user: dict = Depends(require_user)) -> dict:
    sources = workspace.search_documents(user["id"], request.question, request.limit)
    if sources:
        answer = " ".join(source["text"] for source in sources[:2])
        caveat = "Results are retrieved only from documents in your private workspace. Lexical matching is used; relevance must be checked by the user."
    else:
        answer = "No matching information was found in your private workspace documents."
        caveat = "Only your own saved documents were searched. Add a note or change your query."
    return {"question": request.question, "answer": answer, "sources": sources, "scope": "private_workspace", "caveat": caveat}


@app.post("/workspace/agents/investigate", response_model=InvestigationResponse)
def investigate_private_workspace(request: InvestigationRequest, user: dict = Depends(require_user)) -> InvestigationResponse:
    """Run the agent workflow using only the signed-in user's private notes."""
    sources = workspace.search_documents(user["id"], request.question, limit=4)
    if sources:
        answer = " ".join(source["text"] for source in sources[:2])
        caveat = "Evidence was retrieved only from this account's private workspace documents using lexical matching."
    else:
        answer = "No matching information was found in this account's private workspace documents."
        caveat = "Only this account's private documents were searched. The investigation can still calculate the synthetic city scenario, but it has no private document evidence."
    private_knowledge = {
        "question": request.question,
        "answer": answer,
        "sources": sources,
        "scope": "private_workspace",
        "caveat": caveat,
    }
    try:
        prior_memories = workspace.find_agent_memories(user["id"], request.question, request.scenario.district_id, limit=3)
        result = investigate(request.question, request.scenario, knowledge_override=private_knowledge)
        current_metrics = result.get("scenario_result", {})
        for memory in prior_memories:
            historical_metrics = memory.get("scenario_result", {})
            comparison = {}
            for domain in ("traffic", "water", "electricity"):
                previous_value = historical_metrics.get(domain, {}).get("projected")
                current_value = current_metrics.get(domain, {}).get("projected")
                if isinstance(previous_value, (int, float)) and isinstance(current_value, (int, float)):
                    comparison[domain] = {
                        "previous_projected": previous_value,
                        "current_projected": current_value,
                        "absolute_change": round(current_value - previous_value, 4),
                        "percent_change": round(((current_value - previous_value) / previous_value) * 100, 2) if previous_value else None,
                    }
            memory["comparison"] = comparison
        result["memory_context"] = {
            "used": bool(prior_memories),
            "count": len(prior_memories),
            "matches": prior_memories,
            "note": "Prior investigations are historical context only. They are not source evidence and do not change simulation calculations.",
        }
        result["memory_saved"] = False
        if request.remember and result.get("verification", {}).get("passed"):
            saved = workspace.save_agent_memory(user["id"], request.question, request.scenario.district_id, result)
            result["memory_saved"] = True
            result["memory_context"]["saved_memory_id"] = saved["id"]
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/workspace/agents/memories")
def list_private_agent_memories(user: dict = Depends(require_user)) -> dict:
    items = workspace.list_agent_memories(user["id"])
    return {"memories": items, "count": len(items), "scope": "private_workspace"}


@app.delete("/workspace/agents/memories/{memory_id}")
def delete_private_agent_memory(memory_id: str, user: dict = Depends(require_user)) -> dict:
    if not workspace.delete_agent_memory(user["id"], memory_id):
        raise HTTPException(status_code=404, detail="Agent memory not found.")
    return {"status": "deleted", "id": memory_id}


@app.delete("/workspace/documents/{document_id}")
def delete_workspace_document(document_id: str, user: dict = Depends(require_user)) -> dict:
    if not workspace.delete_document(user["id"], document_id):
        raise HTTPException(status_code=404, detail="Workspace document not found.")
    return {"status": "deleted", "id": document_id}


@app.middleware("http")
async def apply_request_safety(request: Request, call_next):
    """Apply a small request-body limit and baseline browser security headers."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds the 1 MB limit."},
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/knowledge/status")
def get_knowledge_status() -> dict:
    return {
        "documents_indexed": len(retriever.documents),
        "embedding_mode": "neural" if retriever.embedder else "tfidf_fallback",
        "reranking_enabled": retriever.reranker is not None,
        "note": "Neural models are optional; no model is downloaded automatically.",
    }


@app.get("/ai/status")
def get_ai_status() -> dict:
    """Report local model configuration without making a network request."""
    settings = llm_settings()
    return {
        "enabled": settings["enabled"],
        "provider": settings["provider"],
        "model": settings["model"],
        "base_url": settings["base_url"],
        "mode": "optional_local_generation" if settings["enabled"] else "deterministic_fallback",
        "note": "No external API is used. Enable only when a local Ollama server is available.",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "LifeOS Twin"}


@app.get("/city")
def get_city() -> dict:
    return {
        "city": CITY_NAME,
        "data_label": DATA_LABEL,
        "districts": [
            {
                "id": district_id,
                "name": str(data["name"]),
                "population": int(data["population"]),
                "green_space_percent": float(data["green_space_percent"]),
            }
            for district_id, data in DISTRICTS.items()
        ],
    }


@app.post("/simulate", response_model=ScenarioResult)
def run_simulation(request: ScenarioRequest) -> ScenarioResult:
    try:
        return simulate_scenario(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/scenarios/explore")
def explore_what_if_options(request: WhatIfRequest) -> dict:
    try:
        return explore_scenarios(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/data-sources")
def list_external_data_sources() -> dict:
    return source_catalog()


@app.post("/data-sources/open-meteo/current")
def get_external_current_weather(request: WeatherRequest) -> dict:
    try:
        return fetch_current_weather(request.latitude, request.longitude)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/forecasts/project")
def project_scenario_forecast(request: ForecastRequest) -> dict:
    try:
        return forecast_scenario(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/knowledge/query", response_model=KnowledgeResponse)
def query_knowledge(request: KnowledgeQuery) -> KnowledgeResponse:
    return answer_question(request.question, request.limit)


@app.post("/knowledge/ingest")
def ingest_knowledge(request: KnowledgeIngest) -> dict:
    raise HTTPException(status_code=410, detail="Shared document ingestion is disabled. Use authenticated /workspace/documents instead.")


@app.get("/knowledge/documents")
def list_knowledge_documents() -> dict:
    return {"documents": [], "note": "Shared uploads are disabled. Private documents are available at /workspace/documents with authentication."}


@app.delete("/knowledge/documents/{document_id}")
def delete_knowledge_document(document_id: str) -> dict:
    raise HTTPException(status_code=410, detail="Shared document deletion is disabled. Use authenticated /workspace/documents instead.")


@app.post("/scenarios")
def save_scenario(request: ScenarioSaveRequest) -> dict:
    raise HTTPException(status_code=410, detail="Shared scenario storage is disabled. Use authenticated /workspace/scenarios instead.")


@app.get("/scenarios")
def list_scenarios() -> dict:
    raise HTTPException(status_code=410, detail="Shared scenario storage is disabled. Use authenticated /workspace/scenarios instead.")


@app.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    raise HTTPException(status_code=410, detail="Shared scenario storage is disabled. Use authenticated /workspace/scenarios instead.")


@app.get("/scenarios/{scenario_id}/report.pdf")
def download_scenario_report(scenario_id: str) -> Response:
    raise HTTPException(status_code=410, detail="Shared scenario reports are disabled. Use authenticated /workspace/scenarios instead.")


@app.post("/scenarios/compare/report.pdf")
def download_comparison_report(request: ScenarioCompareRequest) -> Response:
    raise HTTPException(status_code=410, detail="Shared scenario reports are disabled. Use authenticated /workspace/scenarios instead.")


@app.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str) -> dict[str, str]:
    raise HTTPException(status_code=410, detail="Shared scenario storage is disabled. Use authenticated /workspace/scenarios instead.")


@app.post("/scenarios/compare")
def compare_scenarios(request: ScenarioCompareRequest) -> dict:
    raise HTTPException(status_code=410, detail="Shared scenario comparison is disabled. Use authenticated /workspace/scenarios instead.")


@app.get("/scenarios/export/csv")
def export_scenarios_csv() -> PlainTextResponse:
    raise HTTPException(status_code=410, detail="Shared scenario export is disabled. Use authenticated /workspace/scenarios instead.")


@app.post("/agents/investigate", response_model=InvestigationResponse)
def investigate_city(request: InvestigationRequest) -> InvestigationResponse:
    try:
        return investigate(request.question, request.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/agents/investigate/report.pdf")
def export_investigation_report(result: dict) -> Response:
    """Export the exact investigation result supplied by the client; no rerun occurs."""
    if not isinstance(result.get("audit_metadata"), dict) or not result.get("question"):
        raise HTTPException(status_code=422, detail="A completed investigation result with audit metadata is required.")
    pdf = build_investigation_report(result)
    run_id = result.get("audit_metadata", {}).get("run_id", "run")
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="lifeos-investigation-{run_id[:8]}.pdf"'
    })
