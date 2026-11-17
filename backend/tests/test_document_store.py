from app.knowledge.document_store import DocumentStore, chunk_text


def test_chunk_text_splits_long_notes_and_preserves_content():
    text = ("Traffic demand rises with population.\n\n" * 80).strip()
    chunks = chunk_text(text, max_chars=300, overlap=40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert "Traffic demand rises" in " ".join(chunks)


def test_document_store_persists_and_rejects_reserved_ids(tmp_path):
    path = tmp_path / "knowledge.json"
    store = DocumentStore(path)
    record = store.add({
        "id": "USER-NOTE-01",
        "title": "Community mobility note",
        "domain": "mobility",
        "text": "Residents use buses and bicycles for short journeys.",
    })
    assert record["chunks"]
    reloaded = DocumentStore(path)
    assert reloaded.all()[0]["id"] == "USER-NOTE-01"
    assert reloaded.delete("USER-NOTE-01") is True
    assert DocumentStore(path).all() == []


def test_document_store_rejects_reserved_and_duplicate_ids(tmp_path):
    store = DocumentStore(tmp_path / "knowledge.json")
    payload = {"id": "NOVA-PLAN-002", "title": "Reserved", "domain": "planning", "text": "Valid text."}
    try:
        store.add(payload)
        assert False, "Reserved IDs should be rejected"
    except ValueError as exc:
        assert "reserved" in str(exc)
    payload["id"] = "USER-NOTE-02"
    store.add(payload)
    try:
        store.add(payload)
        assert False, "Duplicate IDs should be rejected"
    except ValueError as exc:
        assert "already exists" in str(exc)
