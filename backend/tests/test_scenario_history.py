from fastapi.testclient import TestClient

from app.main import app
from app.services.scenario_store import scenario_store

client = TestClient(app)


def test_legacy_shared_scenario_endpoints_are_disabled():
    assert client.get("/scenarios").status_code == 410
    assert client.post("/scenarios", json={"name": "Shared", "request": {"district_id": "NORTH"}}).status_code == 410
    assert client.get("/scenarios/export/csv").status_code == 410
    assert client.get("/scenarios/unknown/report.pdf").status_code == 410


def test_workspace_scenario_storage_requires_auth_and_returns_private_history():
    import uuid
    suffix = uuid.uuid4().hex[:10]
    account = client.post("/auth/register", json={"email": f"history-{suffix}@example.com", "password": "history-long-password"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    created = client.post("/workspace/scenarios", headers=headers, json={
        "name": "Private baseline", "request": {"district_id": "CENTRAL", "population_change_percent": 10}
    })
    assert created.status_code == 201
    listed = client.get("/workspace/scenarios", headers=headers)
    assert listed.status_code == 200 and listed.json()["count"] == 1
    assert listed.json()["scenarios"][0]["name"] == "Private baseline"


def test_scenario_store_service_retains_its_internal_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(scenario_store, "path", tmp_path / "scenarios.json")
    from app.models.scenario import ScenarioRequest
    for index in range(101):
        scenario_store.create(f"Scenario {index}", ScenarioRequest(district_id="EAST"))
    assert len(scenario_store.list()) == 100
