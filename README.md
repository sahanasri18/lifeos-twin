# LifeOS Twin

**An Agentic Digital Twin for Intelligent City Simulation and Decision-Making**

LifeOS Twin is a local-first decision-support prototype for a fictional city called **Nova City**. It combines a deterministic Python simulation, an interactive Three.js city interface, a knowledge retrieval layer, authenticated private workspaces, and a controlled multi-agent investigation workflow.

> **Scope:** This project uses synthetic city data. It is an experimental prototype, not a real-world infrastructure controller, engineering forecast, or production security system.

## Current milestone: 24

Milestone 24 adds an optional live weather connector while keeping external weather separate from the synthetic infrastructure calculations.

### Main features

- Interactive 3D city scene with five fictional districts.
- Deterministic traffic, water-demand, and electricity-demand scenario calculations.
- Scenario history, comparison, and PDF reports.
- What-if exploration for multiple alternative scenarios.
- Assumption-based 1–10 year projections for traffic, water, and electricity.
- Offline knowledge retrieval over the built-in Nova City knowledge corpus.
- Account registration, login, and user-isolated scenario and document workspaces.
- Private knowledge search and authenticated agent investigations.
- A deterministic investigation planner, dependency-aware task execution, verification checks, and execution traces.
- Account-private investigation memory with controls to opt out, list, and delete saved memories.
- Three rule-based domain specialists that compare alternatives and report consensus and dissent.
- Optional current-weather snapshots from Open-Meteo using coordinates supplied by the user.

### Important limitations

- City and infrastructure values are synthetic and calculated by deterministic rules.
- Forecasts use user-supplied growth assumptions; they are not produced by a trained predictive model.
- The planner and specialist agents are rule-based Python components, not autonomous LLM agents.
- External weather is shown with provider attribution and timestamps. It is not blended into city simulation calculations, and no weather request is made automatically on page load.
- Internal verification checks consistency and structure; they do not prove that source information or model assumptions are true.
- This prototype has not undergone a production security review. Do not deploy it publicly with development secrets or permissive CORS settings.

## Project structure

```text
lifeos-twin/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── knowledge/
│   │   ├── models/
│   │   └── services/
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── architecture.md
│   ├── authentication-and-workspaces.md
│   ├── external-data-integration.md
│   ├── predictive-forecasting.md
│   └── ...
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── README.md
```

## Run locally

### 1. Start the backend

Python 3.11 or newer is recommended.

```bash
cd backend
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install dependencies and start the API:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Open the frontend

Open `frontend/index.html` in a modern browser with WebGL enabled. The frontend is static and does not require a Node build step. Three.js is loaded from jsDelivr, so an internet connection is needed for the 3D library.

The frontend uses `http://127.0.0.1:8000` as its default API address. See `frontend/README.md` to configure a different API URL.

## Run tests

From the `backend/` directory, with dependencies installed:

```bash
pytest
```

The project includes automated tests for simulation, API behavior, authentication and workspace isolation, knowledge retrieval, agent planning and execution, scenario exploration, forecasting, and external data integration.

## Documentation

- [System architecture](docs/architecture.md)
- [Authentication and private workspaces](docs/authentication-and-workspaces.md)
- [Knowledge engine](docs/knowledge-engine.md)
- [Agent memory](docs/agent-memory.md)
- [Decision intelligence](docs/decision-intelligence.md)
- [Multi-agent debate](docs/multi-agent-debate.md)
- [Predictive forecasting](docs/predictive-forecasting.md)
- [External data integration](docs/external-data-integration.md)

## GitHub Pages

The static frontend can be published through GitHub Pages using the workflow in `.github/workflows/pages.yml`. GitHub Pages hosts only the frontend; the Python API must run separately for simulation and knowledge features. A separately hosted API must be configured in the frontend.

## Security note

Set a strong, private `LIFEOS_AUTH_SECRET` and a private persistent `LIFEOS_WORKSPACE_DB` before any deployment. Do not commit real credentials, tokens, local databases, or private user data. Review the authentication documentation and restrict CORS to the exact frontend origin before exposing an API publicly.
