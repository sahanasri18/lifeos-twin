"""Small, repeatable retrieval evaluation for the synthetic Nova City corpus."""
from app.knowledge.retriever import HybridRetriever

CASES = [
    ("population growth water demand pipes", "NOVA-WATER-001"),
    ("electricity demand commercial growth grid", "NOVA-ENERGY-001"),
    ("traffic pressure vehicle demand roads", "NOVA-TRAFFIC-001"),
    ("city district green space planning", "NOVA-PLAN-001"),
    ("model assumptions synthetic data limitations", "NOVA-METHOD-001"),
]


def evaluate() -> dict[str, float]:
    retriever = HybridRetriever()
    hits_at_1 = 0
    hits_at_3 = 0
    reciprocal_rank = 0.0
    for query, expected_id in CASES:
        results = retriever.search(query, limit=3)
        ids = [item.get("document_id", item["id"]) for item in results]
        if ids and ids[0] == expected_id:
            hits_at_1 += 1
        if expected_id in ids:
            hits_at_3 += 1
            reciprocal_rank += 1 / (ids.index(expected_id) + 1)
    total = len(CASES)
    return {
        "queries": float(total),
        "hit_rate_at_1": hits_at_1 / total,
        "hit_rate_at_3": hits_at_3 / total,
        "mean_reciprocal_rank": reciprocal_rank / total,
    }


if __name__ == "__main__":
    for key, value in evaluate().items():
        print(f"{key}: {value:.3f}" if key != "queries" else f"{key}: {int(value)}")
