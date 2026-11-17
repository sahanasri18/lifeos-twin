"""SQLite-backed accounts and isolated personal workspaces.

This module uses only the Python standard library. Set LIFEOS_AUTH_SECRET to a
random secret before exposing the API beyond a local development environment.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from threading import RLock

from app.models.scenario import ScenarioRequest
from app.services.simulation import simulate_scenario

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "workspaces.sqlite3"
_DEV_SECRET = "lifeos-twin-development-secret-change-before-deployment"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class WorkspaceService:
    def __init__(self, db_path: str | Path | None = None, secret: str | None = None):
        self.db_path = Path(db_path or os.getenv("LIFEOS_WORKSPACE_DB", str(_DEFAULT_DB)))
        self.secret = (secret or os.getenv("LIFEOS_AUTH_SECRET") or _DEV_SECRET).encode("utf-8")
        self._lock = RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workspace_scenarios (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_scenarios_user
                    ON workspace_scenarios(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS workspace_documents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_documents_user
                    ON workspace_documents(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS workspace_agent_memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    district_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_memories_user
                    ON workspace_agent_memories(user_id, created_at DESC);
            """)

    @staticmethod
    def _password_hash(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return f"pbkdf2_sha256$310000${_b64(salt)}${_b64(digest)}"

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, rounds, salt_text, digest_text = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt_text), int(rounds))
            return hmac.compare_digest(actual, _unb64(digest_text))
        except (ValueError, TypeError):
            return False

    def register(self, email: str, password: str) -> dict:
        normalized = email.strip().lower()
        if len(normalized) > 254 or "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address.")
        if len(password) < 10 or len(password) > 128:
            raise ValueError("Password must contain 10–128 characters.")
        user_id = str(uuid.uuid4())
        try:
            with self._connect() as db:
                db.execute("INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)",
                           (user_id, normalized, self._password_hash(password), int(time.time())))
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists.") from exc
        return {"id": user_id, "email": normalized}

    def authenticate(self, email: str, password: str) -> dict | None:
        normalized = email.strip().lower()
        with self._connect() as db:
            row = db.execute("SELECT id,email,password_hash FROM users WHERE email=?", (normalized,)).fetchone()
        if not row or not self._verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "email": row["email"]}

    def issue_token(self, user: dict, lifetime_seconds: int = 43_200) -> str:
        payload = {"sub": user["id"], "email": user["email"], "exp": int(time.time()) + lifetime_seconds}
        body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _b64(hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest())
        return f"{body}.{signature}"

    @property
    def uses_development_secret(self) -> bool:
        return hmac.compare_digest(self.secret, _DEV_SECRET.encode("utf-8"))

    def verify_token(self, token: str) -> dict | None:
        try:
            body, supplied = token.split(".", 1)
            expected = _b64(hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(supplied, expected):
                return None
            payload = json.loads(_unb64(body))
            if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(time.time()):
                return None
            with self._connect() as db:
                user = db.execute("SELECT id,email FROM users WHERE id=?", (payload.get("sub"),)).fetchone()
            if not user:
                return None
            return {"id": user["id"], "email": user["email"]}
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def create_scenario(self, user_id: str, name: str, request: ScenarioRequest) -> dict:
        clean = " ".join(name.split())
        if not clean or len(clean) > 80:
            raise ValueError("Scenario name must contain 1–80 characters.")
        result = simulate_scenario(request)
        record = {"id": str(uuid.uuid4()), "name": clean, "created_at": int(time.time()),
                  "request": request.model_dump(mode="json"), "result": result.model_dump(mode="json")}
        with self._connect() as db:
            db.execute("INSERT INTO workspace_scenarios(id,user_id,name,payload,created_at) VALUES(?,?,?,?,?)",
                       (record["id"], user_id, clean, json.dumps(record), record["created_at"]))
        return record

    def list_scenarios(self, user_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM workspace_scenarios WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_scenarios(self, user_id: str, scenario_ids: list[str]) -> list[dict]:
        if len(scenario_ids) < 2 or len(scenario_ids) > 5 or len(set(scenario_ids)) != len(scenario_ids):
            raise ValueError("Select between two and five unique workspace scenarios.")
        placeholders = ",".join("?" for _ in scenario_ids)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT id,payload FROM workspace_scenarios WHERE user_id=? AND id IN ({placeholders})",
                [user_id, *scenario_ids],
            ).fetchall()
        records = {row["id"]: json.loads(row["payload"]) for row in rows}
        if len(records) != len(scenario_ids):
            raise KeyError("One or more workspace scenarios were not found.")
        return [records[scenario_id] for scenario_id in scenario_ids]

    def get_scenario(self, user_id: str, scenario_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT payload FROM workspace_scenarios WHERE id=? AND user_id=?",
                (scenario_id, user_id),
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def delete_scenario(self, user_id: str, scenario_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM workspace_scenarios WHERE id=? AND user_id=?", (scenario_id, user_id))
        return cursor.rowcount == 1

    def create_document(self, user_id: str, title: str, domain: str, body: str) -> dict:
        clean_title, clean_domain = " ".join(title.split()), domain.strip().lower()
        if not clean_title or len(clean_title) > 160 or len(clean_domain) > 32 or len(body) > 20_000:
            raise ValueError("Document title, domain or content is outside the allowed limits.")
        if not body.strip():
            raise ValueError("Document content cannot be blank.")
        record = {"id": str(uuid.uuid4()), "title": clean_title, "domain": clean_domain,
                  "characters": len(body), "created_at": int(time.time())}
        with self._connect() as db:
            db.execute("INSERT INTO workspace_documents(id,user_id,title,domain,body,created_at) VALUES(?,?,?,?,?,?)",
                       (record["id"], user_id, clean_title, clean_domain, body, record["created_at"]))
        return record

    def list_documents(self, user_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT id,title,domain,length(body) AS characters,created_at FROM workspace_documents WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def search_documents(self, user_id: str, question: str, limit: int = 4) -> list[dict]:
        """Search only the authenticated user's documents using transparent lexical scoring."""
        import math
        import re
        from collections import Counter

        tokens = lambda value: re.findall(r"[a-z0-9]+", value.lower())
        query_terms = tokens(question)
        if not query_terms:
            return []
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,title,domain,body,created_at FROM workspace_documents WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        if not rows:
            return []
        docs = []
        frequencies = Counter()
        tokenized = []
        for row in rows:
            terms = tokens(f"{row['title']} {row['body']}")
            counts = Counter(terms)
            tokenized.append((row, terms, counts))
            frequencies.update(set(terms))
        total = len(rows)
        average_length = sum(len(terms) for _, terms, _ in tokenized) / total
        query_counts = Counter(query_terms)
        for row, terms, counts in tokenized:
            score = 0.0
            for term, query_count in query_counts.items():
                frequency = counts[term]
                if not frequency:
                    continue
                document_frequency = frequencies[term]
                inverse_frequency = math.log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(terms) / max(average_length, 1))
                score += inverse_frequency * (frequency * 2.5 / denominator) * query_count
            if score > 0:
                docs.append({
                    "id": row["id"], "document_id": row["id"], "title": row["title"],
                    "domain": row["domain"], "text": row["body"], "score": round(score, 4),
                    "retrieval": "workspace_bm25", "created_at": row["created_at"],
                })
        docs.sort(key=lambda item: item["score"], reverse=True)
        return docs[: max(1, min(int(limit), 10))]

    def delete_document(self, user_id: str, document_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM workspace_documents WHERE id=? AND user_id=?", (document_id, user_id))
        return cursor.rowcount == 1


    def save_agent_memory(self, user_id: str, question: str, district_id: str, result: dict) -> dict:
        """Persist a compact, account-private record of a completed investigation."""
        clean_question = " ".join(question.split())
        if not clean_question or len(clean_question) > 500:
            raise ValueError("Memory question must contain 1–500 characters.")
        if district_id not in {"CENTRAL", "NORTH", "EAST", "SOUTH", "WEST"}:
            raise ValueError("Unknown district for agent memory.")
        scenario = result.get("scenario_result", {})
        payload = {
            "question": clean_question,
            "district_id": district_id,
            "scenario_result": scenario,
            "recommendation": str(result.get("recommendation", ""))[:2000],
            "findings": [str(item)[:500] for item in result.get("findings", [])[:6]],
            "evidence_ids": [str(item)[:100] for item in result.get("evidence_ids", [])[:20]],
            "knowledge_scope": str(result.get("knowledge_scope", "private_workspace")),
            "verification_passed": bool(result.get("verification", {}).get("passed", False)),
        }
        memory_id = str(uuid.uuid4())
        created_at = int(time.time())
        with self._connect() as db:
            db.execute(
                "INSERT INTO workspace_agent_memories(id,user_id,question,district_id,payload,created_at) VALUES(?,?,?,?,?,?)",
                (memory_id, user_id, clean_question, district_id, json.dumps(payload), created_at),
            )
        return {"id": memory_id, "created_at": created_at, **payload}

    @staticmethod
    def _memory_terms(value: str) -> set[str]:
        import re
        ignored = {"what", "when", "where", "which", "would", "could", "should", "does", "this", "that", "with", "from", "into", "about", "your", "have", "there", "their", "they", "them", "then", "than", "the", "and", "for", "are", "was", "were", "how", "does", "happen", "happens"}
        return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2 and term not in ignored}

    def find_agent_memories(self, user_id: str, question: str, district_id: str, limit: int = 3) -> list[dict]:
        """Return lexically related memories from this account only; memories are context, not evidence."""
        query_terms = self._memory_terms(question)
        if not query_terms:
            return []
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,question,district_id,payload,created_at FROM workspace_agent_memories WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
                (user_id,),
            ).fetchall()
        matches = []
        for row in rows:
            payload = json.loads(row["payload"])
            memory_terms = self._memory_terms(row["question"])
            overlap = len(query_terms & memory_terms) / max(len(query_terms | memory_terms), 1)
            same_district = row["district_id"] == district_id
            score = overlap + (0.15 if same_district else 0.0)
            if score >= 0.12:
                matches.append({
                    "id": row["id"], "question": row["question"], "district_id": row["district_id"],
                    "created_at": row["created_at"], "similarity": round(score, 4),
                    "same_district": same_district, "scenario_result": payload.get("scenario_result", {}),
                    "recommendation": payload.get("recommendation", ""),
                    "verification_passed": payload.get("verification_passed", False),
                })
        matches.sort(key=lambda item: (item["similarity"], item["created_at"]), reverse=True)
        return matches[: max(1, min(int(limit), 5))]

    def list_agent_memories(self, user_id: str, limit: int = 20) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,question,district_id,payload,created_at FROM workspace_agent_memories WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, max(1, min(int(limit), 50))),
            ).fetchall()
        records = []
        for row in rows:
            payload = json.loads(row["payload"])
            records.append({"id": row["id"], "question": row["question"], "district_id": row["district_id"],
                            "created_at": row["created_at"], "verification_passed": payload.get("verification_passed", False),
                            "recommendation": payload.get("recommendation", "")})
        return records

    def delete_agent_memory(self, user_id: str, memory_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM workspace_agent_memories WHERE id=? AND user_id=?", (memory_id, user_id))
        return cursor.rowcount == 1


workspace = WorkspaceService()
