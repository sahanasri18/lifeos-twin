"""Small, provenance-aware adapters for public external datasets.

The first live adapter reads current conditions from Open-Meteo. It is contextual
weather data only; it is never substituted for traffic, water or electricity
measurements in the synthetic city model.
"""
from datetime import datetime, timezone
from typing import Any

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def source_catalog() -> dict[str, Any]:
    return {
        "sources": [
            {
                "id": "open_meteo_current_weather",
                "name": "Open-Meteo Current Weather",
                "provider": "Open-Meteo",
                "kind": "live_api",
                "domains": ["weather", "environmental_context"],
                "authentication": "none",
                "attribution": "Weather data by Open-Meteo.com",
                "url": "https://open-meteo.com/",
                "limitations": [
                    "Weather observations/estimates are contextual and do not measure city infrastructure capacity.",
                    "Availability depends on the external provider and network connection.",
                    "Coordinates must be supplied by the user; no location is inferred.",
                ],
            }
        ],
        "note": "Only sources listed here are connected. No external data is silently mixed into synthetic simulation results.",
    }


def fetch_current_weather(latitude: float, longitude: float, client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch a compact current-weather snapshot and retain provider provenance."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "timezone": "UTC",
    }
    owns_client = client is None
    http = client or httpx.Client(timeout=8.0, follow_redirects=False)
    try:
        response = http.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Open-Meteo could not provide a current weather response.") from exc
    finally:
        if owns_client:
            http.close()

    current = payload.get("current") if isinstance(payload, dict) else None
    if not isinstance(current, dict) or not all(key in current for key in ("time", "temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "weather_code")):
        raise RuntimeError("Open-Meteo returned an incomplete current-weather payload.")

    return {
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "attribution": "Weather data by Open-Meteo.com",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "observed_at": current["time"],
        "timezone": payload.get("timezone", "UTC"),
        "current": {
            "temperature_c": current["temperature_2m"],
            "relative_humidity_percent": current["relative_humidity_2m"],
            "precipitation_mm": current["precipitation"],
            "wind_speed_kmh": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
        },
        "integration_status": "live_external_data",
        "usage_note": "Context only. These values do not update or validate the synthetic traffic, water or electricity model.",
    }
