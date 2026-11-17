from app.services.planner import PlannedTask
from app.services.task_executor import execute_plan


def test_executor_runs_tasks_in_dependency_order_and_passes_results():
    tasks = [
        PlannedTask("source", "source_agent", "load source"),
        PlannedTask("analysis", "analysis_agent", "analyze", ("source",)),
        PlannedTask("decision", "decision_agent", "decide", ("analysis",)),
    ]
    handlers = {
        "source": lambda ctx, results: {"value": ctx["value"]},
        "analysis": lambda ctx, results: {"value": results["source"]["value"] * 2},
        "decision": lambda ctx, results: {"answer": results["analysis"]["value"] + 1},
    }
    result = execute_plan(tasks, handlers, {"value": 20})
    assert result["status"] == "completed"
    assert result["execution_order"] == ["source", "analysis", "decision"]
    assert result["results"]["decision"]["answer"] == 41
    assert result["completed_count"] == 3


def test_executor_blocks_dependent_tasks_after_failure_but_runs_independent_tasks():
    tasks = [
        PlannedTask("broken", "broken_agent", "fails"),
        PlannedTask("blocked", "blocked_agent", "depends", ("broken",)),
        PlannedTask("independent", "independent_agent", "independent"),
    ]
    def fail(_ctx, _results):
        raise RuntimeError("controlled test failure")
    result = execute_plan(tasks, {"broken": fail, "blocked": lambda *_: {"ok": True}, "independent": lambda *_: {"ok": True}})
    statuses = {item["task_id"]: item["status"] for item in result["trace"]}
    assert result["status"] == "partial_failure"
    assert statuses == {"broken": "failed", "independent": "completed", "blocked": "skipped"}
    assert result["failed_count"] == 1
    assert result["skipped_count"] == 1


def test_executor_rejects_invalid_plans_and_missing_handlers():
    cyclic = [PlannedTask("a", "a", "a", ("b",)), PlannedTask("b", "b", "b", ("a",))]
    try:
        execute_plan(cyclic, {})
    except ValueError as exc:
        assert "invalid task plan" in str(exc)
    else:
        raise AssertionError("Invalid plan should be rejected")

    valid = [PlannedTask("a", "a", "a")]
    result = execute_plan(valid, {})
    assert result["trace"][0]["status"] == "failed"
    assert "No execution handler" in result["trace"][0]["error"]
