# Milestone 23 — Predictive intelligence and forecasting

The `POST /forecasts/project` endpoint adds a transparent time horizon to the existing deterministic scenario simulator. A request supplies a validated district scenario, a forecast horizon from 1 to 10 years, and separate annual growth assumptions for traffic, water, and electricity. The response includes Year 0 (the scenario's simulated starting value) through the selected final year.

For each metric, the service applies compound growth:

`value at year n = scenario starting value × (1 + annual growth rate)^n`

Annual rates are user-provided assumptions, bounded from -20% to +50%. The API does not learn or infer these rates from history. Negative rates reduce the projection; zero rates keep it flat. The forecast UI uses the district and population-change controls from the Scenario Studio and exposes the three annual rates and horizon for adjustment.

## Interpretation and limits

This is an assumption-based projection layered on the fictional Nova City model, not a trained predictive model, statistical forecast, or real-world city prediction. It does not use historical time-series data, confidence intervals, seasonality, causal learning, external feeds, weather, policy changes, shocks, costs, infrastructure capacity, or engineering constraints. Constant annual growth is a simplifying assumption. The result should be used to explore sensitivity to assumptions, not to make operational planning decisions.
