"""Transparent, deterministic impact calculations for the synthetic city."""

from app.models.scenario import MetricResult, ScenarioRequest, ScenarioResult
from app.services.city_data import DISTRICTS


ASSUMPTIONS = [
    "Population growth changes residential water demand and a share of daily traffic.",
    "Commercial growth affects traffic and electricity demand using fixed demo factors.",
    "Green-space changes slightly reduce traffic pressure; they do not model land use or weather.",
    "All baseline values and coefficients are synthetic demonstration assumptions.",
]


def _metric(baseline: float, factor: float, unit: str) -> MetricResult:
    projected = round(baseline * factor, 2)
    change = 0.0 if baseline == 0 else round(((projected - baseline) / baseline) * 100, 2)
    return MetricResult(
        baseline=round(baseline, 2),
        projected=projected,
        change_percent=change,
        unit=unit,
    )


def simulate_scenario(request: ScenarioRequest) -> ScenarioResult:
    district = DISTRICTS.get(request.district_id)
    if district is None:
        raise ValueError(f"Unknown district '{request.district_id}'. Choose from: {', '.join(DISTRICTS)}")

    population_delta = request.population_change_percent / 100
    commercial_delta = request.commercial_growth_percent / 100
    green_delta = request.green_space_change_percent / 100

    # These coefficients are explicit demo assumptions, not learned predictions.
    traffic_factor = 1 + (0.65 * population_delta) + (0.55 * commercial_delta) - (0.08 * green_delta)
    water_factor = 1 + (0.90 * population_delta) + (0.10 * commercial_delta)
    electricity_factor = 1 + (0.45 * population_delta) + (0.85 * commercial_delta)

    traffic_factor = max(0.1, traffic_factor)
    water_factor = max(0.1, water_factor)
    electricity_factor = max(0.1, electricity_factor)

    traffic = _metric(float(district["daily_vehicles"]), traffic_factor, "vehicles/day")
    water = _metric(float(district["daily_water_m3"]), water_factor, "m³/day")
    electricity = _metric(float(district["daily_electricity_mwh"]), electricity_factor, "MWh/day")

    highest_change = max(traffic.change_percent, water.change_percent, electricity.change_percent)
    risk = "high" if highest_change >= 40 else "moderate" if highest_change >= 15 else "low"

    return ScenarioResult(
        district_id=request.district_id,
        traffic=traffic,
        water=water,
        electricity=electricity,
        risk_level=risk,
        assumptions=ASSUMPTIONS.copy(),
    )
