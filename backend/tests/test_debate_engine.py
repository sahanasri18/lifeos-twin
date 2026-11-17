from copy import deepcopy

from app.services.debate_engine import run_specialist_debate, verify_specialist_debate


def sample_analysis():
    # Deliberately create competing domain preferences.
    return {"ranking": [
        {"option_id": "a", "label": "A", "score": 90, "risk_level": "low", "metrics": {"traffic": {"change_percent": 1}, "water": {"change_percent": 30}, "electricity": {"change_percent": 20}}},
        {"option_id": "b", "label": "B", "score": 88, "risk_level": "low", "metrics": {"traffic": {"change_percent": 25}, "water": {"change_percent": 1}, "electricity": {"change_percent": 2}}},
        {"option_id": "c", "label": "C", "score": 80, "risk_level": "moderate", "metrics": {"traffic": {"change_percent": 10}, "water": {"change_percent": 10}, "electricity": {"change_percent": 1}}},
        {"option_id": "d", "label": "D", "score": 70, "risk_level": "high", "metrics": {"traffic": {"change_percent": 15}, "water": {"change_percent": 15}, "electricity": {"change_percent": 15}}},
    ]}


def test_specialists_review_all_options_and_disagree():
    debate = run_specialist_debate(sample_analysis())
    assert len(debate["agents"]) == 3
    assert all(len(agent["evaluations"]) == 4 for agent in debate["agents"])
    assert len({agent["preferred_option_id"] for agent in debate["agents"]}) > 1
    assert debate["dissent"]
    assert debate["challenges"]


def test_consensus_is_deterministic_and_verified():
    analysis = sample_analysis()
    first = run_specialist_debate(analysis)
    second = run_specialist_debate(analysis)
    assert first == second
    assert verify_specialist_debate(first, analysis)


def test_tie_uses_original_decision_score_then_option_id():
    analysis = sample_analysis()
    for option in analysis["ranking"]:
        option["metrics"]["traffic"]["change_percent"] = 0
        option["metrics"]["water"]["change_percent"] = 0
        option["metrics"]["electricity"]["change_percent"] = 0
    analysis["ranking"][0]["score"] = analysis["ranking"][1]["score"] = 99
    debate = run_specialist_debate(analysis)
    assert debate["consensus_option_id"] == "a"
    assert debate["consensus_strength"] == "unanimous"


def test_invalid_or_incomplete_metrics_are_rejected():
    analysis = sample_analysis()
    del analysis["ranking"][0]["metrics"]["water"]
    try:
        run_specialist_debate(analysis)
        assert False, "Expected validation error"
    except ValueError:
        pass


def test_tampered_vote_count_fails_verification():
    analysis = sample_analysis()
    debate = run_specialist_debate(analysis)
    tampered = deepcopy(debate)
    tampered["votes"]["a"] += 1
    assert not verify_specialist_debate(tampered, analysis)
