from app.knowledge.retriever import retriever


def answer_question(question: str, limit: int = 4) -> dict:
    sources = retriever.search(question, limit=limit)
    if not sources:
        answer = "The Nova City knowledge base does not contain enough relevant information to answer this question."
    else:
        # Extractive response: no LLM is used, so claims remain directly tied to retrieved notes.
        answer = " ".join(source["text"] for source in sources[:2])
    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "caveat": (
            "Nova City documents and figures are synthetic demonstration material. "
            "The default offline mode uses BM25 + TF-IDF and extractive answers. "
            "Neural embeddings and cross-encoder reranking are optional and activate only "
            "when their dependencies, model files, and environment settings are available."
        ),
    }
