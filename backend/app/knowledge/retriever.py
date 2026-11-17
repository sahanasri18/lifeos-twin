"""Hybrid lexical/vector-style retrieval using only the Python standard library.

The vector component is TF-IDF cosine similarity, not a neural embedding model.
This keeps the MVP fully offline and avoids claiming an embedding model is trained.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.knowledge.corpus import DOCUMENTS
from app.knowledge.neural import load_optional_embedder, load_optional_reranker

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from", "how", "if", "in", "is", "it", "of", "on", "or", "the", "to", "what", "when", "where", "which", "with", "would", "you", "your"}


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]


class HybridRetriever:
    def __init__(self, documents: list[dict[str, Any]] | None = None) -> None:
        source_documents = documents if documents is not None else DOCUMENTS
        self.documents: list[dict[str, Any]] = []
        for source in source_documents:
            chunks = source.get("chunks") or [source["text"]]
            for chunk_index, chunk in enumerate(chunks, start=1):
                item = dict(source)
                item["document_id"] = source["id"]
                item["id"] = source["id"] if len(chunks) == 1 else f"{source['id']}-C{chunk_index:02d}"
                item["text"] = chunk
                self.documents.append(item)
        self._terms = [_tokens(f"{d['title']} {d['text']}") for d in self.documents]
        self._doc_freq: Counter[str] = Counter()
        for terms in self._terms:
            self._doc_freq.update(set(terms))
        self._idf = {
            term: math.log(1 + (len(self.documents) - count + 0.5) / (count + 0.5))
            for term, count in self._doc_freq.items()
        }
        self._avg_len = sum(map(len, self._terms)) / max(1, len(self._terms))
        self.embedder = load_optional_embedder()
        self.reranker = load_optional_reranker()
        self._document_vectors = (
            self.embedder.encode([f"{d['title']}\n{d['text']}" for d in self.documents])
            if self.embedder and self.documents else []
        )

    def refresh(self) -> None:
        """Reload built-in and locally ingested documents into the index."""
        self.__init__(DOCUMENTS)

    def search(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        query_terms = _tokens(query)
        if not query_terms:
            return []
        query_counts = Counter(query_terms)
        ranked: list[dict[str, Any]] = []
        query_vector = self.embedder.encode([query])[0] if self.embedder else None
        for document, terms in zip(self.documents, self._terms):
            counts = Counter(terms)
            length = len(terms)
            bm25 = 0.0
            for term, q_count in query_counts.items():
                frequency = counts[term]
                if frequency:
                    k1, b = 1.5, 0.75
                    denom = frequency + k1 * (1 - b + b * length / max(self._avg_len, 1))
                    bm25 += self._idf.get(term, 0.0) * (frequency * (k1 + 1) / denom) * q_count
            # TF-IDF cosine: sparse vectors represented by dictionaries.
            doc_vec = {t: (1 + math.log(c)) * self._idf.get(t, 0.0) for t, c in counts.items()}
            query_vec = {t: (1 + math.log(c)) * self._idf.get(t, 0.0) for t, c in query_counts.items()}
            dot = sum(value * doc_vec.get(term, 0.0) for term, value in query_vec.items())
            q_norm = math.sqrt(sum(v * v for v in query_vec.values()))
            d_norm = math.sqrt(sum(v * v for v in doc_vec.values()))
            cosine = dot / (q_norm * d_norm) if q_norm and d_norm else 0.0
            # Normalize BM25 per query below; vector score contributes independently.
            semantic = 0.0
            if query_vector is not None:
                doc_vector = self._document_vectors[len(ranked)]
                semantic = sum(a * b for a, b in zip(query_vector, doc_vector))
            ranked.append({"document": document, "bm25": bm25, "cosine": cosine, "semantic": semantic})
        query_vocabulary = set(query_terms)
        max_bm25 = max((item["bm25"] for item in ranked), default=0.0) or 1.0
        for item in ranked:
            overlap = len(query_vocabulary.intersection(set(item["document"]["title"].lower().split()) | set(item["document"]["text"].lower().split())))
            lexical = 0.65 * (item["bm25"] / max_bm25) + 0.35 * item["cosine"]
            item["score"] = 0.55 * lexical + 0.45 * max(0.0, item["semantic"]) if query_vector is not None else lexical
            item["overlap_ratio"] = overlap / max(1, len(query_vocabulary))
        ranked.sort(key=lambda item: item["score"], reverse=True)
        # Rerank a bounded candidate set, then retain the original retrieval score
        # separately so users can inspect how the first-stage search performed.
        candidates = [item for item in ranked if item["score"] > 0 and (query_vector is not None or item["overlap_ratio"] >= 0.4)][:20]
        if self.reranker and candidates:
            rerank_scores = self.reranker.score(query, [f"{x['document']['title']}\n{x['document']['text']}" for x in candidates])
            for item, rerank_score in zip(candidates, rerank_scores):
                item["retrieval_score"] = item["score"]
                item["rerank_score"] = rerank_score
                item["score"] = 0.5 * item["score"] + 0.5 * (1 / (1 + math.exp(-max(-30, min(30, rerank_score)))))
            candidates.sort(key=lambda item: item["score"], reverse=True)
        results = []
        for item in candidates[: max(1, min(limit, 10))]:
            doc = item["document"]
            results.append({
                "id": doc["id"], "document_id": doc.get("document_id", doc["id"]), "title": doc["title"], "domain": doc["domain"],
                "text": doc["text"], "score": round(item["score"], 4),
                "retrieval": "hybrid_neural" if query_vector is not None else "hybrid_bm25_tfidf",
                "reranked": "rerank_score" in item,
                "retrieval_score": round(item.get("retrieval_score", item["score"]), 4),
                "rerank_score": round(item["rerank_score"], 4) if "rerank_score" in item else None,
                "chunk_count": len(doc.get("chunks", [doc["text"]])),
            })
        return results


retriever = HybridRetriever()
