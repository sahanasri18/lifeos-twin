"""Side-by-side what-if analysis using the existing deterministic simulator."""
from app.models.scenario_explorer import WhatIfRequest
from app.services.simulation import simulate_scenario

METRICS = ("traffic", "water", "electricity")


def explore_scenarios(request: WhatIfRequest) -> dict:
    results = []
    for option in request.options:
        result = simulate_scenario(option.scenario).model_dump()
        results.append({"option_id": option.option_id, "label": option.label.strip(), "scenario": option.scenario.model_dump(), "result": result})

    baseline = results[0]["result"]
    comparisons = []
    for item in results:
        metric_deltas = {}
        for metric in METRICS:
            value = item["result"][metric]
            base = baseline[metric]
            metric_deltas[metric] = {
                "projected": value["projected"],
                "change_percent": value["change_percent"],
                "difference_from_first": round(value["projected"] - base["projected"], 2),
            }
        comparisons.append({**item, "deltas": metric_deltas})

    # The first option is a reference chosen by the caller, not an automatic recommendation.
    return {
        "district_id": request.options[0].scenario.district_id,
        "reference_option_id": request.options[0].option_id,
        "options": comparisons,
        "comparison_note": "Differences are measured against the first submitted option. No option is automatically recommended.",
        "limitations": [
            "All values come from the fictional Nova City deterministic model.",
            "The same simulation coefficients are applied independently to each option.",
            "This comparison does not include cost, delivery time, equity, weather, capacity constraints, or engineering feasibility.",
        ],
    }
