import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.workspace_service import WorkspaceService

client = TestClient(app)


def test_registration_login_and_token_validation(tmp_path):
    service = WorkspaceService(tmp_path / "auth.sqlite3", secret="test-secret")
    user = service.register("Person@Example.com", "a-long-test-password")
    assert user["email"] == "person@example.com"
    token = service.issue_token(user)
    assert service.verify_token(token)["id"] == user["id"]
    assert service.authenticate("PERSON@example.com", "a-long-test-password")["id"] == user["id"]
    assert service.authenticate("person@example.com", "wrong-password") is None
    assert service.verify_token(token + "x") is None


def test_duplicate_registration_and_weak_password_are_rejected(tmp_path):
    service = WorkspaceService(tmp_path / "auth.sqlite3", secret="test-secret")
    service.register("person@example.com", "a-long-test-password")
    try:
        service.register("PERSON@example.com", "another-long-password")
        assert False, "duplicate email should fail"
    except ValueError as exc:
        assert "already exists" in str(exc)
    try:
        service.register("other@example.com", "short")
        assert False, "weak password should fail"
    except ValueError as exc:
        assert "10" in str(exc)


def test_workspace_records_are_isolated_by_user(tmp_path):
    service = WorkspaceService(tmp_path / "workspace.sqlite3", secret="test-secret")
    first = service.register("first@example.com", "first-long-password")
    second = service.register("second@example.com", "second-long-password")
    from app.models.scenario import ScenarioRequest
    scenario = service.create_scenario(first["id"], "First user's scenario", ScenarioRequest(district_id="NORTH"))
    doc = service.create_document(first["id"], "Private note", "water", "Private water planning note.")
    assert len(service.list_scenarios(first["id"])) == 1
    assert service.list_scenarios(second["id"]) == []
    assert service.list_documents(first["id"])[0]["id"] == doc["id"]
    assert service.list_documents(second["id"]) == []
    assert service.delete_scenario(second["id"], scenario["id"]) is False
    assert service.delete_document(second["id"], doc["id"]) is False
    assert len(service.list_scenarios(first["id"])) == 1


def test_workspace_api_requires_auth_and_isolates_users():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"first-{suffix}@example.com", "password": "first-long-password"})
    second = client.post("/auth/register", json={"email": f"second-{suffix}@example.com", "password": "second-long-password"})
    assert first.status_code == 201
    assert second.status_code == 201
    token_one = first.json()["access_token"]
    token_two = second.json()["access_token"]
    assert client.get("/workspace/scenarios").status_code == 401
    created = client.post("/workspace/scenarios", headers={"Authorization": f"Bearer {token_one}"}, json={
        "name": "Private North scenario", "request": {"district_id": "NORTH", "population_change_percent": 10}
    })
    assert created.status_code == 201
    scenario_id = created.json()["id"]
    assert client.get("/workspace/scenarios", headers={"Authorization": f"Bearer {token_two}"}).json()["count"] == 0
    denied_delete = client.delete(f"/workspace/scenarios/{scenario_id}", headers={"Authorization": f"Bearer {token_two}"})
    assert denied_delete.status_code == 404
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token_one}"}).status_code == 200


def test_workspace_document_crud_requires_owner_token():
    suffix = uuid.uuid4().hex[:10]
    account = client.post("/auth/register", json={"email": f"docs-{suffix}@example.com", "password": "docs-long-password"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    created = client.post("/workspace/documents", headers=headers, json={
        "title": "Water plan", "domain": "water", "text": "Keep private district water planning notes here."
    })
    assert created.status_code == 201
    document_id = created.json()["id"]
    listed = client.get("/workspace/documents", headers=headers)
    assert listed.json()["count"] == 1
    deleted = client.delete(f"/workspace/documents/{document_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/workspace/documents", headers=headers).json()["count"] == 0


def test_workspace_scenario_report_requires_owner_token():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"report-a-{suffix}@example.com", "password": "report-long-password"}).json()
    second = client.post("/auth/register", json={"email": f"report-b-{suffix}@example.com", "password": "report-long-password"}).json()
    headers_one = {"Authorization": f"Bearer {first['access_token']}"}
    headers_two = {"Authorization": f"Bearer {second['access_token']}"}
    created = client.post("/workspace/scenarios", headers=headers_one, json={
        "name": "Private report scenario", "request": {"district_id": "EAST", "population_change_percent": 15}
    })
    scenario_id = created.json()["id"]
    assert client.get(f"/workspace/scenarios/{scenario_id}/report.pdf").status_code == 401
    assert client.get(f"/workspace/scenarios/{scenario_id}/report.pdf", headers=headers_two).status_code == 404
    report = client.get(f"/workspace/scenarios/{scenario_id}/report.pdf", headers=headers_one)
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")


def test_workspace_comparison_report_only_includes_owner_scenarios():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"compare-a-{suffix}@example.com", "password": "compare-long-password"}).json()
    second = client.post("/auth/register", json={"email": f"compare-b-{suffix}@example.com", "password": "compare-long-password"}).json()
    headers_one = {"Authorization": f"Bearer {first['access_token']}"}
    headers_two = {"Authorization": f"Bearer {second['access_token']}"}
    ids = []
    for district in ("NORTH", "SOUTH"):
        response = client.post("/workspace/scenarios", headers=headers_one, json={
            "name": f"{district} option", "request": {"district_id": district, "population_change_percent": 12}
        })
        ids.append(response.json()["id"])
    payload = {"scenario_ids": ids}
    assert client.post("/workspace/scenarios/compare/report.pdf", json=payload).status_code == 401
    assert client.post("/workspace/scenarios/compare/report.pdf", headers=headers_two, json=payload).status_code == 404
    report = client.post("/workspace/scenarios/compare/report.pdf", headers=headers_one, json=payload)
    assert report.status_code == 200 and report.content.startswith(b"%PDF")


def test_frontend_authentication_and_private_workspace_wiring():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="auth-gate"' in html
    assert 'id="auth-form"' in html
    assert 'id="logout-button"' in html
    assert "'/auth/me'" in js
    assert "'/workspace/scenarios'" in js
    assert "'/workspace/documents'" in js
    assert "lifeos_access_token" in js
    assert "sessionStorage.removeItem('lifeos_access_token')" in js



def test_private_knowledge_search_requires_auth_and_isolates_documents():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"private-a-{suffix}@example.com", "password": "private-long-password"}).json()
    second = client.post("/auth/register", json={"email": f"private-b-{suffix}@example.com", "password": "private-long-password"}).json()
    headers_one = {"Authorization": f"Bearer {first['access_token']}"}
    headers_two = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.post("/workspace/knowledge/query", json={"question":"water capacity"}).status_code == 401
    created = client.post("/workspace/documents", headers=headers_one, json={
        "title":"North water capacity plan", "domain":"water",
        "text":"North district private reservoir capacity and water demand planning notes."
    })
    assert created.status_code == 201
    found = client.post("/workspace/knowledge/query", headers=headers_one, json={"question":"reservoir water capacity", "limit":5})
    assert found.status_code == 200
    assert found.json()["scope"] == "private_workspace"
    assert len(found.json()["sources"]) == 1
    assert found.json()["sources"][0]["id"] == created.json()["id"]
    hidden = client.post("/workspace/knowledge/query", headers=headers_two, json={"question":"reservoir water capacity", "limit":5})
    assert hidden.status_code == 200
    assert hidden.json()["sources"] == []
    assert "No matching information" in hidden.json()["answer"]


def test_private_agent_investigation_uses_only_calling_users_documents():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"agent-a-{suffix}@example.com", "password": "agent-long-password"}).json()
    second = client.post("/auth/register", json={"email": f"agent-b-{suffix}@example.com", "password": "agent-long-password"}).json()
    headers_one = {"Authorization": f"Bearer {first['access_token']}"}
    headers_two = {"Authorization": f"Bearer {second['access_token']}"}
    payload = {
        "question": "What do my notes say about reservoir water capacity?",
        "scenario": {"district_id": "NORTH", "population_change_percent": 20},
    }
    assert client.post("/workspace/agents/investigate", json=payload).status_code == 401
    created = client.post("/workspace/documents", headers=headers_one, json={
        "title": "Private reservoir plan", "domain": "water",
        "text": "Private reservoir capacity should be reviewed before approving new district demand.",
    })
    assert created.status_code == 201

    first_result = client.post("/workspace/agents/investigate", headers=headers_one, json=payload)
    assert first_result.status_code == 200
    result_one = first_result.json()
    assert result_one["knowledge_scope"] == "private_workspace"
    assert result_one["evidence_ids"] == [created.json()["id"]]
    assert result_one["verification"]["passed"] is True
    assert result_one["scenario_result"]["water"]["projected"] > 0

    second_result = client.post("/workspace/agents/investigate", headers=headers_two, json=payload)
    assert second_result.status_code == 200
    result_two = second_result.json()
    assert result_two["knowledge_scope"] == "private_workspace"
    assert result_two["evidence_ids"] == []
    assert result_two["verification"]["passed"] is True
    assert "no private document evidence" in result_two["knowledge_caveat"]
    assert any(step["agent"] == "city_context" and step["status"] == "limited" for step in result_two["execution_trace"])


def test_private_agent_investigation_frontend_is_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="private-investigation-form"' in html
    assert "'/workspace/agents/investigate'" in js
    assert "Evidence scope:" in js


def test_private_agent_memory_is_saved_reused_and_account_isolated():
    suffix = uuid.uuid4().hex[:10]
    first = client.post("/auth/register", json={"email": f"memory-a-{suffix}@example.com", "password": "memory-long-password"}).json()
    second = client.post("/auth/register", json={"email": f"memory-b-{suffix}@example.com", "password": "memory-long-password"}).json()
    headers_one = {"Authorization": f"Bearer {first['access_token']}"}
    headers_two = {"Authorization": f"Bearer {second['access_token']}"}
    payload = {
        "question": "Compare water demand and reservoir capacity after population growth",
        "scenario": {"district_id": "NORTH", "population_change_percent": 20},
        "remember": True,
    }
    first_run = client.post("/workspace/agents/investigate", headers=headers_one, json=payload)
    assert first_run.status_code == 200
    first_data = first_run.json()
    assert first_data["memory_saved"] is True
    assert first_data["memory_context"]["used"] is False

    second_run = client.post("/workspace/agents/investigate", headers=headers_one, json=payload)
    assert second_run.status_code == 200
    second_data = second_run.json()
    assert second_data["memory_context"]["used"] is True
    assert second_data["memory_context"]["count"] == 1
    assert second_data["memory_context"]["matches"][0]["district_id"] == "NORTH"
    assert set(second_data["memory_context"]["matches"][0]["comparison"]) == {"traffic", "water", "electricity"}
    assert "historical context only" in second_data["memory_context"]["note"].lower()

    other_user = client.get("/workspace/agents/memories", headers=headers_two)
    assert other_user.status_code == 200
    assert other_user.json()["count"] == 0
    assert other_user.json()["memories"] == []

    own_memories = client.get("/workspace/agents/memories", headers=headers_one)
    assert own_memories.status_code == 200
    assert own_memories.json()["count"] == 2
    memory_id = own_memories.json()["memories"][0]["id"]
    assert client.delete(f"/workspace/agents/memories/{memory_id}", headers=headers_two).status_code == 404
    assert client.delete(f"/workspace/agents/memories/{memory_id}", headers=headers_one).status_code == 200


def test_private_agent_memory_can_be_disabled_by_user():
    suffix = uuid.uuid4().hex[:10]
    account = client.post("/auth/register", json={"email": f"memory-off-{suffix}@example.com", "password": "memory-long-password"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    response = client.post("/workspace/agents/investigate", headers=headers, json={
        "question": "Review traffic flow under higher population growth",
        "scenario": {"district_id": "EAST", "population_change_percent": 10},
        "remember": False,
    })
    assert response.status_code == 200
    assert response.json()["memory_saved"] is False
    assert response.json()["memory_context"]["count"] == 0
    listed = client.get("/workspace/agents/memories", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["count"] == 0
