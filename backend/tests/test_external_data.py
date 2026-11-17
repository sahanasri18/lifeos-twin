import httpx
import pytest

from app.services.external_data import fetch_current_weather, source_catalog


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "timezone": "UTC",
            "current": {
                "time": "2026-11-15T00:00",
                "temperature_2m": 30.4,
                "relative_humidity_2m": 72,
                "precipitation": 0.2,
                "wind_speed_10m": 12.5,
                "weather_code": 2,
            },
        }


class FakeClient:
    def __init__(self):
        self.params = None

    def get(self, url, params):
        assert url == "https://api.open-meteo.com/v1/forecast"
        self.params = params
        return FakeResponse()


def test_weather_adapter_maps_provider_payload_and_preserves_provenance():
    client = FakeClient()
    result = fetch_current_weather(13.08, 80.27, client=client)
    assert result["source"] == "Open-Meteo"
    assert result["integration_status"] == "live_external_data"
    assert result["coordinates"] == {"latitude": 13.08, "longitude": 80.27}
    assert result["current"]["temperature_c"] == 30.4
    assert result["current"]["relative_humidity_percent"] == 72
    assert "Open-Meteo.com" in result["attribution"]
    assert "do not update" in result["usage_note"]
    assert client.params["timezone"] == "UTC"


def test_weather_adapter_rejects_incomplete_provider_payload():
    class IncompleteClient:
        def get(self, url, params):
            class Response:
                def raise_for_status(self):
                    pass
                def json(self):
                    return {"current": {"temperature_2m": 20}}
            return Response()

    with pytest.raises(RuntimeError, match="incomplete"):
        fetch_current_weather(0, 0, client=IncompleteClient())


def test_weather_adapter_translates_provider_network_errors():
    class FailingClient:
        def get(self, url, params):
            raise httpx.ConnectError("offline")

    with pytest.raises(RuntimeError, match="could not provide"):
        fetch_current_weather(0, 0, client=FailingClient())


def test_catalog_has_explicit_provider_scope_and_no_auth_requirement():
    source = source_catalog()["sources"][0]
    assert source["authentication"] == "none"
    assert source["domains"] == ["weather", "environmental_context"]
    assert source["url"] == "https://open-meteo.com/"
