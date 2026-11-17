# Milestone 24 — Live External Data Integration

## Connected provider

LifeOS Twin includes one live public-data adapter: **Open-Meteo Current Weather**.
The backend requests current temperature, relative humidity, precipitation, wind
speed and weather code from `https://api.open-meteo.com/v1/forecast`. The user
supplies latitude and longitude; the application does not infer or request device
location. The request has an eight-second timeout and does not follow redirects.

No API key is required for this public endpoint. Provider attribution is included
in the returned response and frontend display: **Weather data by Open-Meteo.com**.
See <https://open-meteo.com/> for provider terms and attribution requirements.

## API

- `GET /data-sources` — lists the configured provider, its domain and limitations.
- `POST /data-sources/open-meteo/current` — accepts `latitude` (-90..90) and
  `longitude` (-180..180), then returns a timestamped provider snapshot.

A provider/network failure returns HTTP 502. An incomplete provider payload is
rejected rather than represented as a successful observation. The response
contains source, source URL, attribution, coordinates, provider observation time,
fetch time, units, and an explicit `live_external_data` status.

## Data boundaries

- Live weather is contextual environmental information only.
- It does **not** update traffic, water, electricity, risk scores, forecasts or
  decision rankings.
- The city model and its infrastructure metrics remain synthetic demo data.
- A provider response is not an independent verification of the provider's data.
- No external API call is made automatically when the app loads.
- No data is persisted by this connector in this milestone.

## Verification

Automated tests cover provider response mapping, provenance, missing fields,
network failure, catalog disclosure, coordinate validation and API error handling.
Tests use mocked provider responses; they do not make a live request to Open-Meteo.
A successful local test run therefore verifies the adapter contract, not current
provider availability.
