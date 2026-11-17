"""Validated inputs for deterministic, assumption-based scenario forecasts."""
from pydantic import BaseModel, Field
from app.models.scenario import ScenarioRequest


class ForecastRequest(BaseModel):
    scenario: ScenarioRequest
    years: int = Field(default=5, ge=1, le=10)
    traffic_annual_growth_percent: float = Field(default=2.0, ge=-20, le=50)
    water_annual_growth_percent: float = Field(default=2.5, ge=-20, le=50)
    electricity_annual_growth_percent: float = Field(default=3.0, ge=-20, le=50)
