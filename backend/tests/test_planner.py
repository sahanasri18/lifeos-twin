from app.services.planner import build_plan, validate_plan, TOOL_REGISTRY


def test_planner_builds_dependency_order_and_allowlisted_tools():
    tasks = build_plan("Compare water demand and electricity impact")
    assert validate_plan(tasks)
    ids = {task.task_id for task in tasks}
    assert {"context", "simulate", "water_analysis", "energy_analysis", "decision", "verification"} <= ids
    assert all(task.tool is None or task.tool in TOOL_REGISTRY for task in tasks)
    verify = next(task for task in tasks if task.task_id == "verification")
    assert set(verify.depends_on) == {"context", "simulate", "decision"}


def test_planner_keeps_all_domain_checks_for_side_effects():
    tasks = build_plan("Check traffic congestion")
    agents = {task.agent for task in tasks}
    assert {"traffic_analyst", "water_analyst", "energy_analyst"} <= agents
    traffic = next(task for task in tasks if task.task_id == "traffic_analysis")
    assert "Prioritize" in traffic.objective


def test_planner_rejects_unknown_dependencies_and_duplicate_ids():
    from app.services.planner import PlannedTask
    assert not validate_plan([PlannedTask("a", "agent", "task", ("missing",))])
    assert not validate_plan([PlannedTask("a", "agent", "one"), PlannedTask("a", "agent", "two")])


def test_investigation_exposes_plan_and_tool_policy():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.post("/agents/investigate", json={
        "question": "How does water demand change?",
        "scenario": {"district_id": "EAST", "population_change_percent": 10},
    })
    assert response.status_code == 200
    result = response.json()
    assert len(result["execution_plan"]) == 7
    assert result["tool_registry"]["policy"].startswith("Only explicitly registered")


def test_planner_classifies_intent_and_focus_domains():
    from app.services.planner import classify_question
    result = classify_question("Compare water supply and electricity grid risks")
    assert result["intent"] == "compare_options"
    assert result["focus_domains"] == ["water", "energy"]
    assert result["planning_mode"] == "deterministic_rules"


def test_planner_rejects_dependency_cycles():
    from app.services.planner import PlannedTask
    tasks = [
        PlannedTask("a", "agent_a", "first", ("b",)),
        PlannedTask("b", "agent_b", "second", ("a",)),
    ]
    assert not validate_plan(tasks)


def test_planner_emits_stable_execution_order():
    tasks = build_plan("Check traffic congestion")
    planned = __import__("app.services.planner", fromlist=["plan_as_dicts"]).plan_as_dicts(tasks)
    assert [item["execution_order"] for item in sorted(planned, key=lambda item: item["execution_order"])] == list(range(1, 8))
    assert all(item["execution_order"] > max(
        [next(row["execution_order"] for row in planned if row["task_id"] == dep) for dep in item["depends_on"]] or [0]
    ) for item in planned)
