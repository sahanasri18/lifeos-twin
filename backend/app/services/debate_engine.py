"""Transparent deterministic specialist review and consensus over decision options.

These are rule-based software agents, not independent LLMs or real-world experts.
"""
from __future__ import annotations

import math

DOMAINS = ("traffic", "water", "electricity")
RISK_PENALTY = {"low": 0.0, "moderate": 5.0, "high": 12.0}
AGENT_LABELS = {"traffic": "Traffic specialist", "water": "Water specialist", "electricity": "Electricity specialist"}


def run_specialist_debate(decision_analysis: dict) -> dict:
    options = decision_analysis.get("ranking", [])
    if len(options) != 4:
        raise ValueError("Debate requires exactly four ranked decision options")
    ids = [o.get("option_id") for o in options]
    if len(set(ids)) != 4 or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("Decision options must have unique identifiers")
    if any(not isinstance(o.get("metrics"), dict) for o in options):
        raise ValueError("Each option must include domain metrics")

    agents = []
    for domain in DOMAINS:
        evaluated = []
        for option in options:
            metric = option["metrics"].get(domain)
            if not isinstance(metric, dict) or not isinstance(metric.get("change_percent"), (int, float)):
                raise ValueError(f"Missing valid {domain} metric for {option['option_id']}")
            change = float(metric["change_percent"])
            if not math.isfinite(change):
                raise ValueError("Metric values must be finite")
            risk_penalty = RISK_PENALTY.get(option.get("risk_level"), 12.0)
            score = round(max(0.0, min(100.0, 100.0 - max(0.0, change) - risk_penalty)), 2)
            evaluated.append({"option_id": option["option_id"], "score": score, "change_percent": round(change, 2)})
        evaluated.sort(key=lambda x: (-x["score"], x["option_id"]))
        chosen = evaluated[0]
        agents.append({
            "agent_id": f"{domain}_specialist", "label": AGENT_LABELS[domain],
            "preferred_option_id": chosen["option_id"],
            "preferred_option_score": chosen["score"],
            "reason": f"Lowest modeled {domain} pressure after the shared risk penalty.",
            "evaluations": evaluated,
            "main_concern": f"This review considers {domain} only; it does not establish cost, fairness, or delivery feasibility.",
        })

    votes = {option_id: 0 for option_id in ids}
    for agent in agents:
        votes[agent["preferred_option_id"]] += 1
    # Consensus first uses specialist votes, then the original overall score, then ID.
    by_id = {o["option_id"]: o for o in options}
    consensus_order = sorted(ids, key=lambda oid: (-votes[oid], -float(by_id[oid]["score"]), oid))
    winner_id = consensus_order[0]
    winner_votes = votes[winner_id]
    dissent = [
        {"agent": a["label"], "preferred_option_id": a["preferred_option_id"],
         "preferred_option": by_id[a["preferred_option_id"]]["label"],
         "reason": a["reason"]}
        for a in agents if a["preferred_option_id"] != winner_id
    ]
    challenges = []
    for agent in agents:
        other = next((a for a in agents if a["agent_id"] != agent["agent_id"] and a["preferred_option_id"] != agent["preferred_option_id"]), None)
        if other:
            challenges.append({
                "from_agent": agent["label"], "to_agent": other["label"],
                "challenge": f"Would the preferred option still be best if {other['label'].lower()}'s domain impact were weighted equally?",
                "resolution": "Retained as a trade-off; this deterministic review does not assign extra weight to either domain.",
            })
    return {
        "method": "deterministic_specialist_vote_v1",
        "agents": agents,
        "debate_rounds": [{"round": 1, "summary": "Each specialist independently scored all options using only its own domain metric and the shared risk penalty."},
                          {"round": 2, "summary": "Specialists surfaced cross-domain challenges; conflicting preferences remain visible as dissent."}],
        "challenges": challenges,
        "votes": votes,
        "consensus_order": consensus_order,
        "consensus_option_id": winner_id,
        "consensus_option": by_id[winner_id]["label"],
        "consensus_vote_count": winner_votes,
        "consensus_agent_count": len(agents),
        "consensus_strength": "unanimous" if winner_votes == len(agents) else ("majority" if winner_votes >= 2 else "plurality"),
        "dissent": dissent,
        "unresolved_disagreements": [f"{d['agent']} prefers {d['preferred_option']} based on its own domain-only review." for d in dissent],
        "explanation": "The selected option received the most specialist votes. Ties are broken by the original overall decision score, then option ID.",
        "caveat": "This is a deterministic rule-based debate simulation, not a conversation between autonomous AI models or human infrastructure experts. It uses synthetic scenario outputs and does not change the underlying simulation.",
    }


def verify_specialist_debate(debate: dict, decision_analysis: dict) -> bool:
    try:
        agents = debate["agents"]
        votes = debate["votes"]
        ids = {o["option_id"] for o in decision_analysis["ranking"]}
        if len(agents) != 3 or {a["agent_id"] for a in agents} != {f"{d}_specialist" for d in DOMAINS}:
            return False
        if set(votes) != ids or sum(votes.values()) != 3 or any(not isinstance(v, int) or v < 0 for v in votes.values()):
            return False
        if debate["consensus_option_id"] not in ids or debate["consensus_option_id"] != sorted(ids, key=lambda oid: (-votes[oid], -float(next(o["score"] for o in decision_analysis["ranking"] if o["option_id"] == oid)), oid))[0]:
            return False
        if any(a["preferred_option_id"] not in ids or len(a["evaluations"]) != 4 for a in agents):
            return False
        recalculated = {oid: 0 for oid in ids}
        for agent in agents:
            recalculated[agent["preferred_option_id"]] += 1
        return recalculated == votes and len(debate["dissent"]) == sum(1 for a in agents if a["preferred_option_id"] != debate["consensus_option_id"])
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
