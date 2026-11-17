from app.knowledge import retriever as retriever_module
from app.knowledge.retriever import HybridRetriever


class FakeEmbedder:
    def encode(self, texts):
        # Similar meaning can share a vector even when the exact words differ.
        vectors = []
        for text in texts:
            lowered = text.lower()
            if any(word in lowered for word in ("water", "pipe", "supply")):
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors


class FakeReranker:
    def score(self, query, passages):
        return [2.0 if "water" in passage.lower() else -1.0 for passage in passages]


def test_neural_embedding_mode_can_rank_candidates(monkeypatch):
    monkeypatch.setattr(retriever_module, "load_optional_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(retriever_module, "load_optional_reranker", lambda: None)
    retriever = HybridRetriever()
    results = retriever.search("liquid supply network", limit=3)
    assert results
    assert results[0]["retrieval"] == "hybrid_neural"


def test_reranker_marks_results_and_preserves_first_stage_score(monkeypatch):
    monkeypatch.setattr(retriever_module, "load_optional_embedder", lambda: None)
    monkeypatch.setattr(retriever_module, "load_optional_reranker", lambda: FakeReranker())
    retriever = HybridRetriever()
    results = retriever.search("water demand population growth pipes", limit=3)
    assert results
    assert results[0]["reranked"] is True
    assert "retrieval_score" in results[0]


def test_neural_retrieval_keeps_default_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(retriever_module, "load_optional_embedder", lambda: None)
    monkeypatch.setattr(retriever_module, "load_optional_reranker", lambda: None)
    results = HybridRetriever().search("water demand population growth pipes", limit=3)
    assert results[0]["retrieval"] == "hybrid_bm25_tfidf"
