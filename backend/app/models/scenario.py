from pydantic import BaseModel, Field, field_validator


class ScenarioRequest(BaseModel):
    """A proposed change applied to one synthetic city district."""

    district_id: str = Field(min_length=1, description="Synthetic district identifier")
    population_change_percent: float = Field(default=0, ge=-50, le=300)
    commercial_growth_percent: float = Field(default=0, ge=-50, le=300)
    green_space_change_percent: float = Field(default=0, ge=-100, le=300)

    @field_validator("district_id")
    @classmethod
    def normalize_district_id(cls, value: str) -> str:
        return value.strip().upper()


class MetricResult(BaseModel):
    baseline: float
    projected: float
    change_percent: float
    unit: str


class ScenarioResult(BaseModel):
    district_id: str
    traffic: MetricResult
    water: MetricResult
    electricity: MetricResult
    risk_level: str
    assumptions: list[str]
