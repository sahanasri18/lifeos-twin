"""Deterministic comparison of intervention options for synthetic city scenarios.

Scores are transparent heuristics over the project's illustrative simulation
outputs. They are not calibrated forecasts or real-world cost/benefit estimates.
"""
from __future__ import annotations

import math
from app.models.scenario import ScenarioRequest
from app.services.simulation import simulate_scenario


def _weights(focus_domains: list[str] | None) -> dict[str, float]:
    domains = set(focus_domains or [])
    if len(domains) == 1:
        primary = next(iter(domains))
        weights = {"traffic": 0.2, "water": 0.2, "electricity": 0.2}
        weights[primary] = 0.6
    elif len(domains) == 2:
        weights = {"traffic": 0.2, "water": 0.2, "electricity": 0.2}
        for domain in domains:
            weights[domain] = 0.4
    else:
        weights = {"traffic": 1 / 3, "water": 1 / 3, "electricity": 1 / 3}
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _scenario_options(request: ScenarioRequest) -> list[tuple[str, str, ScenarioRequest]]:
    pop = request.population_change_percent
    commercial = request.commercial_growth_percent
    green = request.green_space_change_percent
    phased = request.model_copy(update={
        "population_change_percent": pop * 0.5,
        "commercial_growth_percent": commercial * 0.5,
    })
    green_buffer = request.model_copy(update={
        "green_space_change_percent": min(300.0, green + 15.0),
    })
    balanced = request.model_copy(update={
        "population_change_percent": pop * 0.5,
        "commercial_growth_percent": commercial * 0.5,
        "green_space_change_percent": min(300.0, green + 15.0),
    })
    return [
        ("proposed_plan", "Submitted scenario", request),
        ("phased_growth", "Phase population and commercial growth", phased),
        ("green_buffer", "Add a 15-point green-space improvement", green_buffer),
        ("balanced_plan", "Phase growth and add green space", balanced),
    ]


def _score(result, weights: dict[str, float]) -> tuple[float, dict]:
    changes = {
        "traffic": result.traffic.change_percent,
        "water": result.water.change_percent,
        "electricity": result.electricity.change_percent,
    }
    # Positive increases are treated as pressure; reductions do not create bonus
    # points beyond the neutral 100 baseline.
    weighted_pressure = sum(weights[key] * max(0.0, value) for key, value in changes.items())
    risk_penalty = {"low": 0.0, "moderate": 5.0, "high": 12.0}.get(result.risk_level, 12.0)
    score = round(max(0.0, min(100.0, 100.0 - weighted_pressure - risk_penalty)), 2)
    return score, {"weighted_positive_change_percent": round(weighted_pressure, 2), "risk_penalty": risk_penalty}


def compare_decisions(request: ScenarioRequest, focus_domains: list[str] | None = None) -> dict:
    weights = _weights(focus_domains)
    options = []
    for option_id, label, scenario in _scenario_options(request):
        result = simulate_scenario(scenario)
        score, score_parts = _score(result, weights)
        options.append({
            "option_id": option_id,
            "label": label,
            "score": score,
            "risk_level": result.risk_level,
            "metrics": {
                "traffic": result.traffic.model_dump(),
                "water": result.water.model_dump(),
                "electricity": result.electricity.model_dump(),
            },
            "score_breakdown": score_parts,
            "scenario_inputs": {
                "population_change_percent": scenario.population_change_percent,
                "commercial_growth_percent": scenario.commercial_growth_percent,
                "green_space_change_percent": scenario.green_space_change_percent,
            },
        })
    options.sort(key=lambda item: (-item["score"], item["option_id"]))
    for rank, option in enumerate(options, start=1):
        option["rank"] = rank
    proposed = next(item for item in options if item["option_id"] == "proposed_plan")
    winner = options[0]
    return {
        "method": "weighted_impact_heuristic_v1",
        "objective": "Reduce modeled positive demand pressure and avoid higher modeled risk.",
        "weights": weights,
        "ranking": options,
        "recommended_option_id": winner["option_id"],
        "recommended_option": winner["label"],
        "score_difference_vs_submitted": round(winner["score"] - proposed["score"], 2),
        "trade_offs": [
            "The score weights the requested domain(s) more heavily but still checks all three systems.",
            "Green-space changes affect traffic only in the current simulation formula; they do not reduce water or electricity demand.",
            "The score excludes money, implementation time, equity, environmental impact and real engineering constraints because the prototype has no validated data for them.",
        ],
        "caveat": "Scores are transparent comparison heuristics over synthetic deterministic outputs, not probabilities, financial returns, or validated city-planning recommendations.",
    }


def verify_decision_analysis(analysis: dict) -> bool:
    try:
        ranking = analysis["ranking"]
        ids = [item["option_id"] for item in ranking]
        scores = [item["score"] for item in ranking]
        ranks = [item["rank"] for item in ranking]
        if len(ranking) != 4 or len(set(ids)) != 4 or ranks != [1, 2, 3, 4]:
            return False
        if any(not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100 for score in scores):
            return False
        if scores != sorted(scores, reverse=True):
            return False
        if analysis["recommended_option_id"] != ids[0]:
            return False
        for item in ranking:
            metrics = item["metrics"]
            if set(metrics) != {"traffic", "water", "electricity"}:
                return False
            for metric in metrics.values():
                if not all(math.isfinite(float(metric[key])) for key in ("baseline", "projected", "change_percent")):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False
