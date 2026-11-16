# Milestone 22 — Scenario intelligence and what-if exploration

The `POST /scenarios/explore` endpoint compares between two and six submitted options using the existing deterministic `simulate_scenario` calculation. Every option must use the same district, option IDs must be unique, and each option inherits the existing bounded population, commercial-growth, and green-space input validation.

The first submitted option is the reference. Each result includes the three modeled indicators, each indicator's percentage change from its district baseline, and the absolute difference from the reference option. The service deliberately does not rank or recommend options: the comparison does not model costs, implementation time, equity, weather, capacity limits, or engineering feasibility.

The Scenario Studio includes three editable option profiles and renders side-by-side modeled results. The district selector is shared with the standard simulation. Inputs are sent to the API and validated server-side; client-side values are not trusted.

All calculations use the fictional Nova City coefficients documented in the simulation service. This is a what-if comparison tool for a synthetic prototype, not a forecast or planning recommendation for a real city.
