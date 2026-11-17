"""Dependency-aware execution engine for the deterministic agent workflow.

The executor does not invent plans or grant tools dynamically. It accepts only a
validated plan and an explicit handler map, runs ready tasks in stable order,
records task outcomes, and blocks downstream tasks after a failed dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from app.services.planner import PlannedTask, topological_order, validate_plan

TaskHandler = Callable[[dict[str, Any], dict[str, dict[str, Any]]], dict[str, Any]]


@dataclass
class TaskExecution:
    task_id: str
    agent: str
    status: str
    depends_on: list[str]
    tool: str | None
    duration_ms: float
    output: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result = {
            "task_id": self.task_id,
            "agent": self.agent,
            "status": self.status,
            "depends_on": self.depends_on,
            "tool": self.tool,
            "duration_ms": round(self.duration_ms, 3),
            "output_keys": sorted(self.output) if self.output else [],
        }
        if self.error:
            result["error"] = self.error
        return result


def execute_plan(
    tasks: list[PlannedTask],
    handlers: dict[str, TaskHandler],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute tasks in dependency order and return outputs plus an audit trace.

    Handlers are selected by task ID, not by user-provided names. Exceptions are
    contained as task failures; tasks depending on failed work are marked skipped.
    Independent tasks may continue, allowing a useful partial execution record.
    """
    if not validate_plan(tasks):
        raise ValueError("Cannot execute an invalid task plan")

    task_by_id = {task.task_id: task for task in tasks}
    order = topological_order(tasks)
    results: dict[str, dict[str, Any]] = {}
    statuses: dict[str, str] = {}
    trace: list[dict[str, Any]] = []
    shared_context = context or {}

    for task_id in order:
        task = task_by_id[task_id]
        failed_dependencies = [dep for dep in task.depends_on if statuses.get(dep) != "completed"]
        if failed_dependencies:
            record = TaskExecution(
                task_id, task.agent, "skipped", list(task.depends_on), task.tool, 0.0,
                error="Blocked by failed or skipped dependencies: " + ", ".join(failed_dependencies),
            )
        elif task_id not in handlers:
            record = TaskExecution(
                task_id, task.agent, "failed", list(task.depends_on), task.tool, 0.0,
                error="No execution handler is registered for this task",
            )
        else:
            started = perf_counter()
            try:
                output = handlers[task_id](shared_context, results)
                if not isinstance(output, dict):
                    raise TypeError("Task handler must return a dictionary")
                results[task_id] = output
                record = TaskExecution(
                    task_id, task.agent, "completed", list(task.depends_on), task.tool,
                    (perf_counter() - started) * 1000, output=output,
                )
            except Exception as exc:  # task failure is recorded, not hidden
                record = TaskExecution(
                    task_id, task.agent, "failed", list(task.depends_on), task.tool,
                    (perf_counter() - started) * 1000,
                    error=f"{type(exc).__name__}: {str(exc)[:240]}",
                )
        statuses[task_id] = record.status
        trace.append(record.as_dict())

    completed = sum(status == "completed" for status in statuses.values())
    failed = sum(status == "failed" for status in statuses.values())
    skipped = sum(status == "skipped" for status in statuses.values())
    return {
        "status": "completed" if failed == 0 and skipped == 0 else "partial_failure",
        "task_count": len(tasks),
        "completed_count": completed,
        "failed_count": failed,
        "skipped_count": skipped,
        "execution_order": order,
        "trace": trace,
        "results": results,
    }
