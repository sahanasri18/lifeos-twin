from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_city_endpoint_lists_five_synthetic_districts():
    response = client.get("/city")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_label"] == "synthetic_demo_data"
    assert len(payload["districts"]) == 5


def test_simulate_endpoint_returns_metrics():
    response = client.post(
        "/simulate",
        json={"district_id": "NORTH", "population_change_percent": 25},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["district_id"] == "NORTH"
    assert payload["water"]["change_percent"] == 22.5


def test_simulate_endpoint_returns_404_for_unknown_district():
    response = client.post("/simulate", json={"district_id": "MOON"})
    assert response.status_code == 404


def test_investigation_endpoint_integrates_planner_simulation_and_verification():
    response = client.post(
        "/agents/investigate",
        json={
            "question": "What happens if population grows in Central District?",
            "scenario": {"district_id": "CENTRAL", "population_change_percent": 20},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["district_id"] == "CENTRAL"
    assert len(payload["execution_plan"]) >= 1
    assert len(payload["findings"]) == 3
    assert payload["scenario_result"]["water"]["projected"] > 0
    assert payload["verification"]["passed"] is True
    assert len(payload["execution_trace"]) >= 5


def test_shared_knowledge_ingestion_is_disabled_and_city_search_remains_read_only():
    created = client.post("/knowledge/ingest", json={
        "id": "INT-TEST-ROUNDTRIP", "title": "Shared test note", "domain": "water",
        "text": "This must not enter the shared knowledge index."
    })
    assert created.status_code == 410
    queried = client.post("/knowledge/query", json={
        "question": "What are the water model limitations?", "limit": 5
    })
    assert queried.status_code == 200
    assert any(source.get("document_id") == "NOVA-WATER-001" for source in queried.json()["sources"])
    assert client.get("/knowledge/documents").json()["documents"] == []
    assert client.delete("/knowledge/documents/INT-TEST-ROUNDTRIP").status_code == 410


def test_shared_scenario_storage_is_disabled():
    assert client.get("/scenarios").status_code == 410
    assert client.post("/scenarios", json={"name":"Shared","request":{"district_id":"NORTH"}}).status_code == 410


def test_frontend_uses_backend_district_ids_and_integrated_agent_endpoint():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    for district_id in ("CENTRAL", "NORTH", "EAST", "SOUTH", "WEST"):
        assert f'value="{district_id}"' in html
    assert "`${API}/agents/investigate`" in js
    assert "`${API}/simulate`" in js
    assert "`${API}/knowledge/query`" in js
    assert "report.pdf" in js
    assert "Download comparison PDF" in js


def test_security_headers_are_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_oversized_request_is_rejected_before_endpoint_processing():
    response = client.post(
        "/knowledge/ingest",
        headers={"content-length": "1000001", "content-type": "application/json"},
        content=b"{}",
    )
    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]


def test_invalid_content_length_is_rejected():
    response = client.post(
        "/knowledge/ingest",
        headers={"content-length": "not-a-number", "content-type": "application/json"},
        content=b"{}",
    )
    assert response.status_code == 400


def test_frontend_renders_task_execution_status_and_details():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "Task execution:" in js
    assert "Task execution details" in js
    assert "duration_ms" in js


def test_investigation_includes_audit_identity_and_input_fingerprint():
    payload = {
        "question": "What happens if population grows in Central District?",
        "scenario": {"district_id": "CENTRAL", "population_change_percent": 20},
    }
    first = client.post("/agents/investigate", json=payload)
    second = client.post("/agents/investigate", json=payload)
    assert first.status_code == second.status_code == 200
    a, b = first.json()["audit_metadata"], second.json()["audit_metadata"]
    assert a["run_id"] != b["run_id"]
    assert a["input_sha256"] == b["input_sha256"]
    assert len(a["input_sha256"]) == 64
    assert a["model_version"] == "lifeos-twin-synthetic-simulation-v1"


def test_investigation_audit_pdf_exports_exact_result():
    investigation = client.post("/agents/investigate", json={
        "question": "What happens if population grows in Central District?",
        "scenario": {"district_id": "CENTRAL", "population_change_percent": 20},
    })
    assert investigation.status_code == 200
    report = client.post("/agents/investigate/report.pdf", json=investigation.json())
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")
    assert "lifeos-investigation-" in report.headers["content-disposition"]


def test_investigation_audit_pdf_rejects_incomplete_payload():
    response = client.post("/agents/investigate/report.pdf", json={"question": "incomplete"})
    assert response.status_code == 422


def test_what_if_explorer_endpoint_compares_multiple_options():
    response = client.post("/scenarios/explore", json={"options": [
        {"option_id": "base", "label": "Reference", "scenario": {"district_id": "NORTH"}},
        {"option_id": "growth", "label": "Growth", "scenario": {"district_id": "NORTH", "population_change_percent": 20}},
    ]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_option_id"] == "base"
    assert len(payload["options"]) == 2
    assert payload["options"][1]["deltas"]["water"]["difference_from_first"] > 0


def test_what_if_explorer_endpoint_rejects_mixed_districts():
    response = client.post("/scenarios/explore", json={"options": [
        {"option_id": "base", "label": "Reference", "scenario": {"district_id": "NORTH"}},
        {"option_id": "other", "label": "Other district", "scenario": {"district_id": "EAST"}},
    ]})
    assert response.status_code == 422


def test_forecast_endpoint_returns_yearly_projection():
    response = client.post("/forecasts/project", json={
        "scenario": {"district_id": "CENTRAL", "population_change_percent": 10},
        "years": 3,
        "traffic_annual_growth_percent": 2,
        "water_annual_growth_percent": 2.5,
        "electricity_annual_growth_percent": 3,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_years"] == 3
    assert len(payload["timeline"]) == 4
    assert payload["timeline"][3]["metrics"]["electricity"]["projected"] > payload["timeline"][0]["metrics"]["electricity"]["projected"]
    assert "not a trained predictive model" in " ".join(payload["limitations"])


def test_forecast_endpoint_validates_growth_and_horizon():
    response = client.post("/forecasts/project", json={
        "scenario": {"district_id": "CENTRAL"}, "years": 20,
        "traffic_annual_growth_percent": 2,
    })
    assert response.status_code == 422


def test_external_data_catalog_discloses_connected_provider_and_limitations():
    response = client.get("/data-sources")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["id"] == "open_meteo_current_weather"
    assert "traffic" not in payload["sources"][0]["domains"]
    assert "synthetic simulation results" in payload["note"]


def test_open_meteo_endpoint_returns_provenance_and_context_only(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "fetch_current_weather", lambda lat, lon: {
        "source": "Open-Meteo", "integration_status": "live_external_data",
        "coordinates": {"latitude": lat, "longitude": lon},
        "current": {"temperature_c": 31.2},
        "usage_note": "Context only.",
    })
    response = client.post("/data-sources/open-meteo/current", json={"latitude": 13.08, "longitude": 80.27})
    assert response.status_code == 200
    payload = response.json()
    assert payload["integration_status"] == "live_external_data"
    assert payload["coordinates"]["latitude"] == 13.08
    assert "Context only" in payload["usage_note"]


def test_open_meteo_endpoint_rejects_invalid_coordinates():
    response = client.post("/data-sources/open-meteo/current", json={"latitude": 190, "longitude": 0})
    assert response.status_code == 422


def test_open_meteo_provider_failure_is_reported_as_bad_gateway(monkeypatch):
    from app import main

    def fail(_lat, _lon):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(main, "fetch_current_weather", fail)
    response = client.post("/data-sources/open-meteo/current", json={"latitude": 13.08, "longitude": 80.27})
    assert response.status_code == 502


def test_frontend_exposes_external_weather_controls_without_auto_fetch():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="weather-latitude"' in html
    assert 'id="weather-longitude"' in html
    assert 'id="fetch-weather"' in html
    assert "`${API}/data-sources/open-meteo/current`" in js
    assert "No external weather data has been requested" in html
    assert "usage_note" in js
