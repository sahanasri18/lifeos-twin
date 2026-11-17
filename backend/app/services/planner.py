"""Inspectable, deterministic planner for LifeOS Twin.

Planning is deliberately rule-based. It classifies the question, selects a
small allow-list of read-only tools, and produces a dependency graph that is
validated for missing links and cycles before execution.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedTask:
    task_id: str
    agent: str
    objective: str
    depends_on: tuple[str, ...] = ()
    tool: str | None = None


TOOL_REGISTRY = {
    "retrieve_city_knowledge": {
        "description": "Retrieve supporting documents from the explicitly selected knowledge scope.",
        "read_only": True,
        "input": ["question", "limit", "knowledge_scope"],
        "output": ["answer", "sources", "caveat"],
        "scopes": ["public_city", "private_workspace"],
    },
    "run_city_simulation": {
        "description": "Calculate traffic, water and electricity impacts using fixed Python formulas.",
        "read_only": True,
        "input": ["district_id", "population_change_percent", "commercial_growth_percent", "green_space_change_percent"],
        "output": ["traffic", "water", "electricity", "risk_level", "assumptions"],
        "scopes": ["synthetic_city_only"],
    },
    "verify_investigation": {
        "description": "Check plan structure, finite non-negative metrics, calculation consistency and evidence provenance.",
        "read_only": True,
        "input": ["scenario_result", "knowledge_sources", "evidence_ids"],
        "output": ["passed", "checks", "issues"],
        "scopes": ["current_investigation_only"],
    },
}

_DOMAIN_TERMS = {
    "traffic": ("traffic", "road", "roads", "transport", "congestion", "vehicle", "vehicles", "mobility"),
    "water": ("water", "supply", "reservoir", "consumption", "drought", "wastewater"),
    "energy": ("energy", "electricity", "power", "grid", "outage", "load"),
}


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def classify_question(question: str) -> dict:
    """Return a transparent intent and domain focus; never invokes a model."""
    normalized = " ".join(question.casefold().split())
    focus = [domain for domain, terms in _DOMAIN_TERMS.items()
             if any(_contains_term(normalized, term) for term in terms)]
    if any(term in normalized for term in ("compare", "versus", " vs ", "alternative", "options")):
        intent = "compare_options"
    elif any(term in normalized for term in ("risk", "safe", "failure", "overload", "shortage", "impact")):
        intent = "assess_risk"
    elif any(term in normalized for term in ("how", "why", "explain", "what does", "what happens")):
        intent = "explain_impact"
    else:
        intent = "scenario_assessment"
    return {
        "intent": intent,
        "focus_domains": focus or ["traffic", "water", "energy"],
        "focus_was_inferred": bool(focus),
        "planning_mode": "deterministic_rules",
    }


def build_plan(question: str) -> list[PlannedTask]:
    """Build a stable seven-task graph, retaining cross-domain side-effect checks."""
    classification = classify_question(question)
    focus = set(classification["focus_domains"])
    tasks = [
        PlannedTask("context", "city_context", "Retrieve relevant evidence only from the selected knowledge scope.", (), "retrieve_city_knowledge"),
        PlannedTask("simulate", "simulation_agent", "Calculate all three city-system impacts with deterministic formulas.", (), "run_city_simulation"),
    ]
    dependencies = ["context", "simulate"]
    for domain in ("traffic", "water", "energy"):
        objective = (
            f"Prioritize the requested {domain} impact, then check cross-domain effects."
            if domain in focus else
            f"Check secondary {domain} effects so the investigation does not miss side effects."
        )
        tasks.append(PlannedTask(f"{domain}_analysis", f"{domain}_analyst", objective, ("simulate",)))
        dependencies.append(f"{domain}_analysis")
    tasks.extend([
        PlannedTask("decision", "decision_analyst", "Combine specialist findings, evidence limits and modeled risk into a cautious recommendation.", tuple(dependencies)),
        PlannedTask("verification", "verification", "Check calculation consistency, evidence provenance and plan integrity.", ("context", "simulate", "decision"), "verify_investigation"),
    ])
    return tasks


def topological_order(tasks: list[PlannedTask]) -> list[str]:
    """Return a deterministic valid execution order or raise ValueError."""
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("Plan contains duplicate task IDs")
    pending = {task_id: set(task.depends_on) for task_id, task in by_id.items()}
    order: list[str] = []
    while pending:
        ready = sorted(task_id for task_id, deps in pending.items() if not deps)
        if not ready:
            raise ValueError("Plan contains a dependency cycle")
        for task_id in ready:
            order.append(task_id)
            pending.pop(task_id)
        for deps in pending.values():
            deps.difference_update(ready)
    return order


def plan_as_dicts(tasks: list[PlannedTask]) -> list[dict]:
    order = {task_id: index + 1 for index, task_id in enumerate(topological_order(tasks))}
    return [
        {"task_id": task.task_id, "agent": task.agent, "objective": task.objective,
         "depends_on": list(task.depends_on), "tool": task.tool, "execution_order": order[task.task_id]}
        for task in tasks
    ]


def validate_plan(tasks: list[PlannedTask]) -> bool:
    """Reject duplicate IDs, missing dependencies, cycles and unregistered tools."""
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        return False
    known = set(ids)
    for task in tasks:
        if task.task_id in task.depends_on or any(dep not in known for dep in task.depends_on):
            return False
        if task.tool is not None and task.tool not in TOOL_REGISTRY:
            return False
    try:
        topological_order(tasks)
    except ValueError:
        return False
    return True
