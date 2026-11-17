"""Transparent compound-growth projections layered on the synthetic simulator."""
from app.models.forecast import ForecastRequest
from app.services.simulation import simulate_scenario

METRICS = {
    "traffic": ("traffic_annual_growth_percent", "vehicles/day"),
    "water": ("water_annual_growth_percent", "m³/day"),
    "electricity": ("electricity_annual_growth_percent", "MWh/day"),
}


def forecast_scenario(request: ForecastRequest) -> dict:
    starting = simulate_scenario(request.scenario).model_dump()
    annual_rates = {
        metric: getattr(request, field) / 100
        for metric, (field, _unit) in METRICS.items()
    }
    yearly = []
    for year in range(request.years + 1):
        values = {}
        for metric, (_field, unit) in METRICS.items():
            start_value = float(starting[metric]["projected"])
            projected = round(start_value * ((1 + annual_rates[metric]) ** year), 2)
            change = 0.0 if start_value == 0 else round((projected / start_value - 1) * 100, 2)
            values[metric] = {
                "projected": projected,
                "change_from_scenario_start_percent": change,
                "annual_growth_assumption_percent": round(annual_rates[metric] * 100, 2),
                "unit": unit,
            }
        yearly.append({"year": year, "metrics": values})

    return {
        "district_id": request.scenario.district_id,
        "forecast_years": request.years,
        "scenario_start": starting,
        "annual_growth_assumptions": {metric: round(rate * 100, 2) for metric, rate in annual_rates.items()},
        "timeline": yearly,
        "method": "Compound annual growth applied to the deterministic scenario starting values.",
        "limitations": [
            "This is an assumption-based projection, not a trained predictive model or a real-world forecast.",
            "Annual growth rates are user-supplied assumptions and are not inferred from historical observations.",
            "The model holds each annual growth rate constant and excludes policy changes, shocks, weather, capacity limits, costs, and infrastructure constraints.",
            "All starting values and simulation coefficients belong to the fictional Nova City demonstration model.",
        ],
    }
