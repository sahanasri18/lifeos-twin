"""Deterministic agent investigation implemented on the task execution engine.

Planning remains rule-based. The execution engine now dispatches concrete task
handlers, passes dependency outputs, records failures, and blocks downstream work.
"""
from __future__ import annotations

import math
import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.services.city_data import DISTRICTS
from app.services.knowledge_service import answer_question
from app.services.simulation import simulate_scenario
from app.services.local_llm import generate_decision, llm_settings, LocalLLMError
from app.services.planner import TOOL_REGISTRY, build_plan, classify_question, plan_as_dicts, validate_plan
from app.services.task_executor import execute_plan
from app.services.decision_engine import compare_decisions, verify_decision_analysis
from app.services.debate_engine import run_specialist_debate, verify_specialist_debate


def _recommendation(district_name: str, simulation) -> str:
    highest = max(
        [("traffic", simulation.traffic.change_percent),
         ("water demand", simulation.water.change_percent),
         ("electricity demand", simulation.electricity.change_percent)],
        key=lambda item: item[1],
    )
    if simulation.risk_level == "high":
        return (
            f"Treat the proposed change in {district_name} as high-impact. Review the "
            f"{highest[0]} increase first, then test a smaller or phased scenario before making a decision."
        )
    if simulation.risk_level == "moderate":
        return (
            f"Review capacity planning for {district_name}, with particular attention to "
            f"{highest[0]}. Compare this scenario with a lower-growth alternative."
        )
    return (
        f"The modeled changes for {district_name} are low under the current assumptions. "
        "Keep monitoring all three demand areas and compare alternatives before deciding."
    )


def _verify(simulation, knowledge: dict, evidence_ids: list[str], planned_tasks: list, scenario_holder, decision_analysis: dict, debate: dict) -> dict:
    metrics = [simulation.traffic, simulation.water, simulation.electricity]
    numeric_valid = all(
        isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
        for metric in metrics for value in (metric.baseline, metric.projected)
    )
    percentages_valid = all(
        isinstance(metric.change_percent, (int, float)) and math.isfinite(metric.change_percent)
        for metric in metrics
    )
    source_records = knowledge.get("sources", [])
    source_ids = [str(source.get("id", "")).strip() for source in source_records if isinstance(source, dict)]
    source_shape_valid = (
        len(source_ids) == len(source_records)
        and all(source_ids)
        and len(source_ids) == len(set(source_ids))
        and all(
            str(source.get("title", "")).strip() and str(source.get("domain", "")).strip()
            for source in source_records if isinstance(source, dict)
        )
    )
    evidence_valid = source_shape_valid and evidence_ids == source_ids
    recalculated = simulate_scenario(scenario_holder.get())
    calculation_consistent = recalculated.model_dump() == simulation.model_dump()
    plan_valid = validate_plan(planned_tasks)
    decision_valid = verify_decision_analysis(decision_analysis)
    debate_valid = verify_specialist_debate(debate, decision_analysis)
    checks = {
        "numeric_outputs_finite_and_non_negative": numeric_valid,
        "percentage_outputs_finite": percentages_valid,
        "simulation_recalculation_matches": calculation_consistent,
        "evidence_source_records_valid": source_shape_valid,
        "evidence_ids_match_retrieved_sources": evidence_valid,
        "task_graph_valid_and_acyclic": plan_valid,
        "decision_options_valid_and_ranked": decision_valid,
        "specialist_debate_consensus_valid": debate_valid,
    }
    issues = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not issues,
        "numeric_outputs_non_negative": numeric_valid,
        "evidence_ids_well_formed": evidence_valid,
        "checks": checks,
        "issues": issues,
        "note": "These checks validate software consistency and evidence structure, not the truth of source documents or the synthetic assumptions.",
    }


class _ScenarioHolder:
    """Small per-call holder used by the verification handler without global state."""
    def __init__(self, scenario):
        self.scenario = scenario

    def get(self):
        return self.scenario


def investigate(question: str, scenario_request, knowledge_override: dict | None = None) -> dict:
    district_id = scenario_request.district_id
    district = DISTRICTS.get(district_id)
    if district is None:
        raise ValueError(f"Unknown district '{district_id}'. Choose from: {', '.join(DISTRICTS)}")

    planner_result = classify_question(question)
    planned_tasks = build_plan(question)
    if not validate_plan(planned_tasks):
        raise RuntimeError("Planner generated an invalid task dependency graph")
    execution_plan = plan_as_dicts(planned_tasks)
    planner_result["task_count"] = len(execution_plan)
    planner_result["execution_order"] = [item["task_id"] for item in sorted(execution_plan, key=lambda item: item["execution_order"])]
    planner_result["selected_tools"] = sorted({task.tool for task in planned_tasks if task.tool})

    context = {
        "question": question,
        "scenario": scenario_request,
        "knowledge_override": knowledge_override,
        "scenario_holder": _ScenarioHolder(scenario_request),
        "planned_tasks": planned_tasks,
    }

    def retrieve_task(ctx, _results):
        # An explicit override, including an empty result, preserves private scope.
        knowledge = ctx["knowledge_override"] if ctx["knowledge_override"] is not None else answer_question(ctx["question"], limit=4)
        return {"knowledge": knowledge, "source_count": len(knowledge.get("sources", [])), "scope": knowledge.get("scope", "public_city")}

    def simulate_task(ctx, _results):
        result = simulate_scenario(ctx["scenario"])
        return {"simulation": result, "district_id": result.district_id, "risk_level": result.risk_level}

    def specialist_task(domain):
        def handler(_ctx, results):
            simulation = results["simulate"]["simulation"]
            metric = {
                "traffic": simulation.traffic,
                "water": simulation.water,
                "energy": simulation.electricity,
            }[domain]
            return {
                "finding": f"{domain}_analyst".replace("_", " ").title() +
                           f": {metric.projected} {metric.unit} ({metric.change_percent:+.2f}% versus baseline).",
                "projected": metric.projected,
                "change_percent": metric.change_percent,
            }
        return handler

    def decision_task(ctx, results):
        simulation = results["simulate"]["simulation"]
        district_name = str(district["name"])
        decision_analysis = compare_decisions(ctx["scenario"], planner_result["focus_domains"])
        debate = run_specialist_debate(decision_analysis)
        return {"recommendation": _recommendation(district_name, simulation), "decision_analysis": decision_analysis, "specialist_debate": debate}

    def verification_task(ctx, results):
        knowledge = results["context"]["knowledge"]
        simulation = results["simulate"]["simulation"]
        evidence_ids = [source.get("id", "") for source in knowledge.get("sources", []) if isinstance(source, dict)]
        decision_analysis = results["decision"]["decision_analysis"]
        debate = results["decision"]["specialist_debate"]
        verification = _verify(simulation, knowledge, evidence_ids, ctx["planned_tasks"], ctx["scenario_holder"], decision_analysis, debate)
        return {"verification": verification}

    handlers = {
        "context": retrieve_task,
        "simulate": simulate_task,
        "traffic_analysis": specialist_task("traffic"),
        "water_analysis": specialist_task("water"),
        "energy_analysis": specialist_task("energy"),
        "decision": decision_task,
        "verification": verification_task,
    }
    execution = execute_plan(planned_tasks, handlers, context)
    if execution["status"] != "completed":
        raise RuntimeError("Agent task execution did not complete: " + str(execution["trace"]))

    task_results = execution["results"]
    knowledge = task_results["context"]["knowledge"]
    simulation = task_results["simulate"]["simulation"]
    evidence_ids = [source["id"] for source in knowledge["sources"]]
    findings = [task_results[f"{domain}_analysis"]["finding"] for domain in ("traffic", "water", "energy")]
    recommendation = task_results["decision"]["recommendation"]
    decision_analysis = task_results["decision"]["decision_analysis"]
    specialist_debate = task_results["decision"]["specialist_debate"]
    verification = task_results["verification"]["verification"]

    llm_status = "disabled"
    llm_summary = None
    try:
        llm_result = generate_decision(question, str(district["name"]), simulation.model_dump(), knowledge["sources"])
        if llm_result:
            llm_status = "used"
            llm_summary = llm_result["summary"]
            recommendation = llm_result["recommendation"]
        elif llm_settings()["enabled"]:
            llm_status = "unavailable"
    except LocalLLMError:
        llm_status = "fallback"

    execution_trace = [
        {
            "agent": "orchestrator",
            "status": "completed",
            "summary": f"Classified the request as {planner_result['intent']}; dispatched {execution['task_count']} tasks in dependency order.",
        }
    ]
    for item in execution["trace"]:
        if item["task_id"] == "context":
            status = "completed" if item["status"] == "completed" and evidence_ids else "limited"
            summary = f"Retrieved {len(evidence_ids)} relevant source document(s) from {knowledge.get('scope', 'public_city')} scope."
        elif item["task_id"] == "verification":
            status = "passed" if verification["passed"] else "failed"
            summary = f"Passed {sum(verification['checks'].values())} of {len(verification['checks'])} verification checks."
        else:
            status = item["status"]
            summary = f"Executed task {item['task_id']} using its registered handler."
        execution_trace.append({"agent": item["agent"], "status": status, "summary": summary})
    execution_trace.append({
        "agent": "llm_decision_agent",
        "status": llm_status,
        "summary": "Generated a constrained explanation from calculated results." if llm_status == "used"
                   else "Local model was not used; the deterministic recommendation remains active.",
    })

    audit_input = {
        "question": question,
        "scenario": scenario_request.model_dump(),
        "knowledge_scope": knowledge.get("scope", "public_city"),
        "evidence_ids": evidence_ids,
    }
    canonical_input = json.dumps(audit_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    audit_metadata = {
        "run_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "input_fingerprint_method": "SHA-256 over canonical question, scenario, knowledge scope and evidence IDs",
        "model_version": "lifeos-twin-synthetic-simulation-v1",
        "reproducibility_note": "The fingerprint identifies these recorded inputs; it does not guarantee identical outputs when optional model settings or source data change.",
    }

    return {
        "question": question,
        "audit_metadata": audit_metadata,
        "district_id": district_id,
        "scenario_result": simulation.model_dump(),
        "findings": findings,
        "recommendation": recommendation,
        "decision_analysis": decision_analysis,
        "specialist_debate": specialist_debate,
        "llm_summary": llm_summary,
        "llm_status": llm_status,
        "evidence_ids": evidence_ids,
        "knowledge_scope": knowledge.get("scope", "public_city"),
        "knowledge_caveat": knowledge.get("caveat", ""),
        "verification": verification,
        "execution_plan": execution_plan,
        "execution_run": {
            "status": execution["status"],
            "task_count": execution["task_count"],
            "completed_count": execution["completed_count"],
            "failed_count": execution["failed_count"],
            "skipped_count": execution["skipped_count"],
            "execution_order": execution["execution_order"],
            "trace": execution["trace"],
        },
        "tool_registry": {
            "available": TOOL_REGISTRY,
            "selected": planner_result["selected_tools"],
            "policy": "Only explicitly registered read-only tools are available to agents; tools cannot access data outside the selected knowledge scope.",
        },
        "planner": planner_result,
        "execution_trace": execution_trace,
        "limitations": [
            "Planning is deterministic rule-based logic; task execution is controlled by explicit Python handlers, not an autonomous LLM agent.",
            "Only the decision explanation can optionally use a local Ollama model; specialist analysis and simulation remain deterministic Python code.",
            "Knowledge evidence is limited to the scope reported in knowledge_scope; private workspace investigations do not query public or other users’ documents.",
            "All city data and knowledge documents are synthetic.",
            "The simulation coefficients are illustrative assumptions, not calibrated forecasts.",
            "Specialist debate and consensus are deterministic rule-based simulations, not autonomous AI agents or human expert review.",
            "Decision scores are transparent heuristics over synthetic outputs; they exclude costs, equity, implementation feasibility and validated engineering constraints.",
            "The recommendation is advisory and must not be used for real infrastructure decisions.",
        ],
    }
