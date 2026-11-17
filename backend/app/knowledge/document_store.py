"""Validated, local JSON document store for user-provided knowledge notes.

Only plain text/Markdown content is accepted. Files are never written using a
user-controlled path, and writes use atomic replacement to avoid partial data.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

STORE_PATH = Path(__file__).with_name("user_documents.json")
MAX_DOCUMENT_CHARS = 20_000
MAX_DOCUMENTS = 100
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")


def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Split text at paragraph/sentence boundaries with bounded overlap."""
    normalized = "\n".join(line.strip() for line in text.replace("\r\n", "\n").splitlines()).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start, end), normalized.rfind(". ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + (1 if normalized[boundary] == "\n" else 1)
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


class DocumentStore:
    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        self._documents: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                self._documents = {
                    item["id"]: item for item in payload
                    if isinstance(item, dict) and isinstance(item.get("id"), str)
                }
        except (OSError, json.JSONDecodeError):
            # A damaged user store must not prevent the API from starting.
            self._documents = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="lifeos-docs-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(list(self._documents.values()), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add(self, document: dict[str, str]) -> dict[str, Any]:
        doc_id = document["id"].strip().upper()
        title = document["title"].strip()
        domain = document["domain"].strip().lower()
        text = document["text"].strip()
        if not _ID_RE.fullmatch(doc_id):
            raise ValueError("Document ID must be 3–64 characters using A–Z, 0–9, _ or -.")
        if doc_id.startswith("NOVA-"):
            raise ValueError("IDs beginning with NOVA- are reserved for built-in city documents.")
        if not title or len(title) > 160:
            raise ValueError("Title must contain 1–160 characters.")
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", domain):
            raise ValueError("Domain must be a simple lowercase label (2–32 characters).")
        if not text or len(text) > MAX_DOCUMENT_CHARS:
            raise ValueError(f"Text must contain 1–{MAX_DOCUMENT_CHARS} characters.")
        if doc_id in self._documents:
            raise ValueError(f"Document ID '{doc_id}' already exists.")
        if len(self._documents) >= MAX_DOCUMENTS:
            raise ValueError(f"The local knowledge store is limited to {MAX_DOCUMENTS} documents.")
        chunks = chunk_text(text)
        record = {"id": doc_id, "title": title, "domain": domain, "text": text, "chunks": chunks}
        self._documents[doc_id] = record
        self._save()
        return record

    def all(self) -> list[dict[str, Any]]:
        return list(self._documents.values())

    def delete(self, doc_id: str) -> bool:
        key = doc_id.strip().upper()
        if key not in self._documents:
            return False
        del self._documents[key]
        self._save()
        return True


store = DocumentStore()
