# Milestone 25 — Infrastructure data ingestion

## Purpose

This milestone introduces a controlled import path for measured traffic, water and electricity observations. It does **not** claim that any public authority dataset has already been connected or independently verified. Users provide the dataset and its provenance metadata.

## API

- `POST /infrastructure-data/import` — accept a JSON dataset and perform basic structural, unit, duplicate, timezone and sanity-range checks.
- `GET /infrastructure-data` — list dataset summaries. Optional `?domain=traffic|water|electricity` filter.
- `GET /infrastructure-data/{dataset_id}` — retrieve the dataset and its accepted observations.

Each import records the dataset name, provider label, source URL, license declaration, data-as-of date, import timestamp, domain, observation count, quality status and row-level issues. Supported metric/unit pairs are intentionally narrow and documented in `backend/app/services/infrastructure_data.py`.

## Quality statuses

- `basic_checks_passed`: all submitted rows passed the implemented checks. This is not a certification of source authenticity or measurement accuracy.
- `review_required`: at least one row or metadata check produced a quality issue. Valid rows can still be retained; rejected rows are excluded.
- An import with no valid observations is rejected.

Observation timestamps must include a timezone. Duplicate keys are timestamp + area + metric. Basic range checks are guardrails, not domain-specific scientific validation.

## Storage and security limits

The current registry is in memory and is cleared when the API process restarts. This is a prototype import workflow, not durable data storage. Do not import personal or confidential records. The source URL is provenance metadata; the backend does not fetch it, crawl it, or verify it. The provider and license fields are declarations supplied by the importer and must be checked against the original publisher's terms.

## Separation from simulation

Imported records are not connected to the synthetic city baseline, decision ranking, agent debate or forecasts. No imported observation silently changes model outputs. A future milestone would need explicit geographic/time matching, source-specific adapters, unit normalization, freshness rules, documented licensing, and an auditable opt-in calibration path before any imported values could influence a simulation.

## Example

```json
{
  "domain": "traffic",
  "dataset_name": "Hourly traffic counts",
  "provider": "Publisher name",
  "source_url": "https://example.org/dataset",
  "license": "CC BY 4.0",
  "data_as_of": "2026-11-14",
  "observations": [
    {
      "observed_at": "2026-11-14T09:00:00+05:30",
      "area": "Central",
      "metric": "vehicle_count",
      "value": 1200,
      "unit": "vehicles/hour"
    }
  ]
}
```

This example is illustrative and is not a real dataset.
