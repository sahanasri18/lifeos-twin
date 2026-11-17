"""Small JSON-backed scenario history store; no external database required."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from app.models.scenario import ScenarioRequest
from app.models.scenario_history import SavedScenario
from app.services.simulation import simulate_scenario


class ScenarioStore:
    def __init__(self, path: str | Path | None = None):
        default = Path(__file__).resolve().parents[2] / "data" / "scenarios.json"
        self.path = Path(path or os.getenv("LIFEOS_SCENARIO_STORE", str(default)))
        self._lock = RLock()

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError("Scenario history is unreadable; preserve the file and inspect it before continuing.") from exc
        if not isinstance(payload, list):
            raise RuntimeError("Scenario history has an invalid format.")
        return payload

    def _write(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="scenarios-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def create(self, name: str, request: ScenarioRequest) -> SavedScenario:
        clean_name = " ".join(name.split())
        if not clean_name:
            raise ValueError("Scenario name cannot be blank.")
        result = simulate_scenario(request)
        record = SavedScenario(
            id=str(uuid.uuid4()), name=clean_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            request=request, result=result,
        )
        with self._lock:
            records = self._read()
            records.insert(0, record.model_dump(mode="json"))
            self._write(records[:100])
        return record

    def list(self) -> list[SavedScenario]:
        with self._lock:
            return [SavedScenario.model_validate(item) for item in self._read()]

    def get_many(self, ids: list[str]) -> list[SavedScenario]:
        records = {item.id: item for item in self.list()}
        missing = [item for item in ids if item not in records]
        if missing:
            raise KeyError(missing[0])
        if len(set(ids)) != len(ids):
            raise ValueError("Scenario IDs must be unique.")
        return [records[item] for item in ids]

    def delete(self, scenario_id: str) -> bool:
        with self._lock:
            records = self._read()
            filtered = [item for item in records if item.get("id") != scenario_id]
            if len(filtered) == len(records):
                return False
            self._write(filtered)
            return True


scenario_store = ScenarioStore()
