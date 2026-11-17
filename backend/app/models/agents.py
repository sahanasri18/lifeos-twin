from pydantic import BaseModel, Field

from app.models.scenario import ScenarioRequest


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    scenario: ScenarioRequest
    remember: bool = True


class AgentStep(BaseModel):
    agent: str
    status: str
    summary: str


class InvestigationResponse(BaseModel):
    question: str
    district_id: str
    scenario_result: dict
    findings: list[str]
    recommendation: str
    decision_analysis: dict = Field(default_factory=dict)
    specialist_debate: dict = Field(default_factory=dict)
    llm_summary: str | None = None
    llm_status: str = "disabled"
    evidence_ids: list[str]
    knowledge_scope: str = "public_city"
    knowledge_caveat: str = ""
    verification: dict
    execution_plan: list[dict]
    execution_run: dict = Field(default_factory=dict)
    tool_registry: dict
    planner: dict = Field(default_factory=dict)
    execution_trace: list[AgentStep]
    limitations: list[str]
    memory_context: dict = Field(default_factory=dict)
    memory_saved: bool = False
    audit_metadata: dict = Field(default_factory=dict)
