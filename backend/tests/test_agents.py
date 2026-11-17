from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_workflow_runs_simulation_and_verification():
    response = client.post("/agents/investigate", json={
        "question": "What happens to water and energy demand if population grows?",
        "scenario": {"district_id": "EAST", "population_change_percent": 25},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["verification"]["passed"] is True
    assert result["scenario_result"]["water"]["change_percent"] > 0
    assert "water_analyst" in [step["agent"] for step in result["execution_trace"]]
    assert result["evidence_ids"]


def test_agent_workflow_rejects_unknown_district():
    response = client.post("/agents/investigate", json={
        "question": "What happens to demand?",
        "scenario": {"district_id": "MOON"},
    })
    assert response.status_code == 404


def test_agent_workflow_marks_unsupported_question_without_fake_sources():
    response = client.post("/agents/investigate", json={
        "question": "How do lunar farms affect submarine insurance?",
        "scenario": {"district_id": "NORTH"},
    })
    assert response.status_code == 200
    assert response.json()["evidence_ids"] == []
    assert response.json()["verification"]["passed"] is True


def test_agent_workflow_reports_deterministic_mode_by_default(monkeypatch):
    monkeypatch.delenv("LIFEOS_LLM_ENABLED", raising=False)
    response = client.post("/agents/investigate", json={
        "question": "How does population growth affect water demand?",
        "scenario": {"district_id": "EAST", "population_change_percent": 15},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["llm_status"] == "disabled"
    assert result["llm_summary"] is None
    assert "llm_decision_agent" in [step["agent"] for step in result["execution_trace"]]


def test_local_llm_result_can_only_supply_explanation(monkeypatch):
    import app.services.agent_workflow as workflow

    monkeypatch.setattr(workflow, "generate_decision", lambda *args: {
        "summary": "Illustrative model explanation.",
        "recommendation": "Review the modeled demand before making a decision.",
    })
    response = client.post("/agents/investigate", json={
        "question": "How does population growth affect water demand?",
        "scenario": {"district_id": "EAST", "population_change_percent": 15},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["llm_status"] == "used"
    assert result["llm_summary"] == "Illustrative model explanation."
    # The model cannot overwrite the numeric simulation payload.
    assert result["scenario_result"]["water"]["projected"] > result["scenario_result"]["water"]["baseline"]


def test_local_llm_failure_keeps_deterministic_recommendation(monkeypatch):
    import app.services.agent_workflow as workflow
    from app.services.local_llm import LocalLLMError

    def fail(*args):
        raise LocalLLMError("offline")

    monkeypatch.setattr(workflow, "generate_decision", fail)
    response = client.post("/agents/investigate", json={
        "question": "How does population growth affect water demand?",
        "scenario": {"district_id": "EAST", "population_change_percent": 15},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["llm_status"] == "fallback"
    assert result["recommendation"]


def test_agent_response_exposes_planning_and_detailed_verification():
    response = client.post("/agents/investigate", json={
        "question": "Compare traffic and water impact",
        "scenario": {"district_id": "EAST", "population_change_percent": 12},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["planner"]["intent"] == "compare_options"
    assert result["planner"]["focus_domains"] == ["traffic", "water"]
    assert result["planner"]["task_count"] == 7
    assert result["verification"]["passed"] is True
    assert all(result["verification"]["checks"].values())
    assert result["tool_registry"]["selected"] == [
        "retrieve_city_knowledge", "run_city_simulation", "verify_investigation"
    ]


def test_agent_verification_rejects_malformed_evidence(monkeypatch):
    import app.services.agent_workflow as workflow
    monkeypatch.setattr(workflow, "answer_question", lambda *args, **kwargs: {
        "sources": [{"id": "DOC-1", "title": "", "domain": "water"}],
        "scope": "public_city", "caveat": "test"
    })
    response = client.post("/agents/investigate", json={
        "question": "How does water demand change?",
        "scenario": {"district_id": "EAST", "population_change_percent": 10},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["verification"]["passed"] is False
    assert result["verification"]["checks"]["evidence_source_records_valid"] is False
    assert "evidence_source_records_valid" in result["verification"]["issues"]


def test_agent_investigation_exposes_real_task_execution_records():
    response = client.post("/agents/investigate", json={
        "question": "Compare traffic and water impact",
        "scenario": {"district_id": "WEST", "population_change_percent": 18},
    })
    assert response.status_code == 200
    payload = response.json()
    run = payload["execution_run"]
    assert run["status"] == "completed"
    assert run["task_count"] == 7
    assert run["completed_count"] == 7
    assert run["failed_count"] == 0
    assert run["skipped_count"] == 0
    assert run["execution_order"] == ["context", "simulate", "energy_analysis", "traffic_analysis", "water_analysis", "decision", "verification"]
    assert all(item["status"] == "completed" for item in run["trace"])
    assert all("duration_ms" in item and "output_keys" in item for item in run["trace"])


def test_private_execution_run_retains_private_scope():
    suffix = __import__("uuid").uuid4().hex[:10]
    account = client.post("/auth/register", json={"email": f"private-run-{suffix}@example.com", "password": "long-private-run-password"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    response = client.post("/workspace/agents/investigate", headers=headers, json={
        "question": "What do my private notes say about water capacity?",
        "scenario": {"district_id": "SOUTH", "population_change_percent": 10},
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["knowledge_scope"] == "private_workspace"
    assert len(payload["decision_analysis"]["ranking"]) == 4
    assert payload["execution_run"]["status"] == "completed"
    context_task = next(item for item in payload["execution_run"]["trace"] if item["task_id"] == "context")
    assert "knowledge" in context_task["output_keys"]


def test_decision_engine_returns_four_ranked_options_with_tradeoffs():
    response = client.post("/agents/investigate", json={
        "question": "Compare water demand options for population growth",
        "scenario": {"district_id": "EAST", "population_change_percent": 30, "commercial_growth_percent": 10},
    })
    assert response.status_code == 200
    payload = response.json()
    analysis = payload["decision_analysis"]
    assert len(analysis["ranking"]) == 4
    assert [item["rank"] for item in analysis["ranking"]] == [1, 2, 3, 4]
    assert analysis["recommended_option_id"] == analysis["ranking"][0]["option_id"]
    assert analysis["weights"]["water"] > analysis["weights"]["traffic"]
    assert len(analysis["trade_offs"]) >= 2
    assert payload["verification"]["checks"]["decision_options_valid_and_ranked"] is True


def test_decision_engine_is_deterministic_and_scores_are_bounded():
    from app.models.scenario import ScenarioRequest
    from app.services.decision_engine import compare_decisions

    scenario = ScenarioRequest(district_id="WEST", population_change_percent=25, commercial_growth_percent=15)
    first = compare_decisions(scenario, ["traffic"])
    second = compare_decisions(scenario, ["traffic"])
    assert first == second
    assert all(0 <= item["score"] <= 100 for item in first["ranking"])
    assert first["weights"]["traffic"] > first["weights"]["water"]


def test_decision_engine_flags_corrupt_rankings():
    from app.models.scenario import ScenarioRequest
    from app.services.decision_engine import compare_decisions, verify_decision_analysis

    analysis = compare_decisions(ScenarioRequest(district_id="NORTH", population_change_percent=20))
    analysis["ranking"][0]["rank"] = 4
    assert verify_decision_analysis(analysis) is False


def test_investigation_returns_verified_specialist_consensus():
    response = client.post("/agents/investigate", json={
        "question": "Compare traffic, water and electricity impacts",
        "scenario": {"district_id": "EAST", "population_change_percent": 28, "commercial_growth_percent": 12},
    })
    assert response.status_code == 200
    payload = response.json()
    debate = payload["specialist_debate"]
    assert len(debate["agents"]) == 3
    assert set(debate["votes"].values()) and sum(debate["votes"].values()) == 3
    assert debate["consensus_option_id"] in {item["option_id"] for item in payload["decision_analysis"]["ranking"]}
    assert payload["verification"]["checks"]["specialist_debate_consensus_valid"] is True
    assert payload["verification"]["passed"] is True

