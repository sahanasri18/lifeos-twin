from fastapi.testclient import TestClient

from app.main import app
from app.knowledge.retriever import HybridRetriever

client = TestClient(app)


def test_hybrid_retriever_finds_water_notes():
    results = HybridRetriever().search("water demand population growth pipes", limit=3)
    assert results
    assert results[0]["id"] == "NOVA-WATER-001"
    assert results[0]["retrieval"] == "hybrid_bm25_tfidf"


def test_query_api_returns_sources_and_caveat():
    response = client.post("/knowledge/query", json={"question": "How does population growth affect water demand?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"]
    assert any(source["id"] == "NOVA-WATER-001" for source in payload["sources"])
    assert "synthetic" in payload["caveat"].lower()


def test_query_api_validates_question_length():
    response = client.post("/knowledge/query", json={"question": "x"})
    assert response.status_code == 422


def test_unrelated_query_does_not_invent_answer():
    response = client.post("/knowledge/query", json={"question": "quantum submarine recipes"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "does not contain enough" in response.json()["answer"]


def test_retrieval_evaluation_has_expected_coverage():
    from evaluate_retrieval import evaluate
    metrics = evaluate()
    assert metrics["queries"] == 5
    assert metrics["hit_rate_at_3"] >= 0.8


def test_shared_document_ingestion_is_disabled_in_favor_of_private_workspaces():
    document = {
        "id": "USER-TEST-INGEST", "title": "Community cycling plan", "domain": "mobility",
        "text": "The community cycling plan adds protected bicycle lanes near schools and public parks.",
    }
    created = client.post("/knowledge/ingest", json=document)
    assert created.status_code == 410
    assert "workspace" in created.json()["detail"].lower()
    assert client.get("/knowledge/documents").json()["documents"] == []
