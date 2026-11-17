from pydantic import BaseModel, Field, field_validator
from app.models.scenario import ScenarioRequest, ScenarioResult


class ScenarioSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    request: ScenarioRequest

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Scenario name cannot be blank.")
        return cleaned


class SavedScenario(BaseModel):
    id: str
    name: str
    created_at: str
    request: ScenarioRequest
    result: ScenarioResult


class ScenarioCompareRequest(BaseModel):
    scenario_ids: list[str] = Field(min_length=2, max_length=5)


class ScenarioComparison(BaseModel):
    scenarios: list[SavedScenario]
    comparison: dict
