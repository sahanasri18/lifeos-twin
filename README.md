# LifeOS Twin

**An Agentic Digital Twin for Intelligent City Simulation and Decision-Making**

LifeOS Twin is an experimental, local-first digital twin for a fictional city. It combines transparent Python simulations with an evidence-oriented knowledge layer and agent workflows. It is a decision-support prototype, not a real-world infrastructure controller.

## Current milestone — Milestone 22

The project includes the simulation backend, interactive Three.js frontend, offline knowledge engine, authenticated private workspaces, and an inspectable multi-agent investigation workflow. Current capabilities include:
- A deterministic fictional city model (Nova City) with five districts
- Traffic, water-demand, and electricity-demand impact calculations
- Scenario evaluation, history, comparison, and PDF reports
- Public synthetic-city knowledge retrieval and private per-account document retrieval
- Account registration/login and owner-isolated scenarios and notes
- Authenticated private agent investigations that do not query another user's documents
- Rule-based question classification and a seven-task dependency plan
- An explicit allow-list of read-only tools with declared inputs, outputs, and data scopes
- Cycle detection and deterministic topological ordering before a plan is accepted
- Mechanical verification of numeric outputs, calculation consistency, evidence record structure, evidence IDs, and plan integrity
- Dependency-aware task execution through explicit Python handlers, with task outputs passed only to dependent tasks
- Per-task execution records, failure handling, dependent-task blocking, and execution summaries
- Account-private agent memory: saves completed investigations, retrieves related prior runs, and allows users to list or delete memories
- Historical memories are displayed separately from source evidence and never alter deterministic simulation calculations
- Deterministic decision comparison evaluates four intervention options, scores them against transparent domain weights, ranks alternatives, and explains trade-offs
- Decision verification checks option count, rank ordering, score bounds, selected winner, and numeric metric integrity
- Three deterministic specialist agents independently score all four options from traffic, water, and electricity perspectives
- A what-if explorer compares 2–6 editable options for the same district across population, commercial-growth, and green-space inputs, with deltas against an explicit reference option
- A two-round debate summary records cross-domain challenges, specialist votes, consensus strength, dissent, and unresolved disagreements
- Consensus tie-breaking is transparent: specialist vote count, original overall decision score, then option ID
- Verification checks specialist identities, option coverage, vote totals, consensus winner, and dissent consistency
- Frontend controls to opt out of saving an investigation and to review/delete private agent memories
- Frontend views for the plan, task execution status, verification checks, and execution trace

The planner is deterministic rules, not an autonomous LLM planner. Simulation values are calculated in Python. Neural retrieval and Ollama generation remain optional and disabled unless configured. City data is synthetic; this is a decision-support prototype, not a live infrastructure system.

## Milestone 18 — Private agent memory

Authenticated workspace investigations can now be saved as account-private memory records. A later investigation retrieves up to three lexically related prior runs, with a same-district boost. Each memory stores the question, district, scenario outputs, recommendation, findings, evidence IDs, and verification status. The UI shows these records as historical context, separate from retrieved documents. Users can turn off saving for an investigation, list their memories, and delete individual records. Memory retrieval is not model training, does not change simulation values, and is not treated as source evidence. The memory table is user-scoped and uses the same account foreign-key cascade as other workspace data.

See [Private Agent Memory](docs/agent-memory.md) for storage, retrieval, API controls, and privacy boundaries.

## Milestone 17 — Controlled task execution

The agent workflow now runs its validated task graph through a dedicated execution engine. The engine dispatches only registered task handlers, passes dependency outputs to downstream tasks, records task status and timing, and blocks dependent tasks when a prerequisite fails. Independent tasks can still complete, producing a partial-failure record. The current handlers are deterministic Python functions; this is not autonomous LLM planning.


## Milestone 22 — Scenario intelligence and what-if exploration

The Scenario Studio can now compare two to six user-defined what-if options for one district. Each option can vary population change, commercial growth, and green-space change. The first submitted option is the explicit reference; results show projected traffic, water, and electricity values, percentage changes from baseline, and absolute differences from the reference. The frontend provides three editable option profiles. The API rejects duplicate option IDs, mixed districts, invalid values, and option counts outside the supported range.

No automatic winner is selected. The model does not include cost, implementation time, equity, weather, capacity limits, or engineering feasibility. All outputs remain synthetic deterministic estimates. See [Scenario Intelligence](docs/scenario-intelligence.md).

Milestone 22 validation: **86 backend tests passed**. Python compilation and frontend JavaScript syntax checks passed. Browser visual testing was not performed.

## Milestone 21 — Investigation audit and export

Every investigation now receives a unique run ID, UTC timestamp, SHA-256 input fingerprint, model version label, and a clear reproducibility limitation. The public investigation view can export the exact displayed result as a PDF audit report, including modeled indicators, ranked options, specialist consensus and dissent, verification status, evidence IDs, fingerprint, and limitations. The report endpoint exports the submitted result without rerunning the investigation. Private source text is not included.

The fingerprint is not a digital signature or proof of truth, and the PDF is not tamper-proof: a client can alter a submitted result before export. The private workspace UI does not yet have a dedicated export button.

## Milestone 20 — Multi-agent debate and consensus

After the four-option decision comparison, three rule-based specialist agents independently evaluate every option: traffic, water, and electricity. Each specialist uses its own domain percentage change and the same risk penalty, then selects its preferred option. A two-round summary records the independent reviews and cross-domain challenges. Consensus is decided by specialist vote count; ties use the original overall decision score and then the option ID. The response includes the vote count, consensus strength, minority preferences, and unresolved disagreements. The frontend displays each specialist position and the dissent/challenge notes.

These are deterministic Python agents, not autonomous LLMs or human experts. Their debate is an auditable simulation of competing domain priorities. It does not modify the scenario simulation or convert synthetic values into real-world evidence.

Milestone 20 validation: **75 backend tests passed**. Python compilation and frontend JavaScript syntax checks passed. Browser visual testing and live optional model inference were not performed.

## Milestone 19 — Decision intelligence

The investigation workflow now compares four deterministic alternatives: the submitted scenario, phased population/commercial growth, a green-space improvement, and a combined phased-growth/green-space option. A transparent weighted-impact heuristic emphasizes the domain(s) detected in the question while retaining checks across traffic, water, and electricity. Each option returns its modeled metrics, risk level, score breakdown, rank, and input assumptions. The response identifies the highest-scoring option and lists important trade-offs. The frontend displays the ranked alternatives and scores.

The scoring method is a prototype heuristic, not a learned optimizer or a real cost-benefit analysis. It does not include financial cost, implementation time, equity, environmental impacts, or engineering feasibility. Green-space changes affect traffic only under the current simulation formula. Scores must not be interpreted as probabilities or real-world forecasts.

Milestone 19 validation: **69 backend tests passed**. Python compilation and frontend JavaScript syntax checks passed. Browser visual testing and live optional model inference were not performed.

## Knowledge query API

Send a POST request to `/knowledge/query` with `{"question": "How does population growth affect water demand?", "limit": 4}` to search the built-in synthetic Nova City corpus. The response includes an extractive answer, ranked source documents, and a caveat. The default offline path uses BM25 + TF-IDF; optional neural retrieval is disabled unless configured. This public endpoint does not search user notes.

## Private workspace notes

Register or sign in through `/auth/register` or `/auth/login`, then send the returned bearer token in the `Authorization: Bearer <token>` header. Use `POST /workspace/documents` to save a private note with `title`, `domain`, and `text`; use `GET /workspace/documents` to list the signed-in user's notes. Private knowledge search and agent investigation are available through `/workspace/knowledge/query` and `/workspace/agents/investigate`. These routes search only the authenticated user's workspace. The legacy shared note-ingestion and deletion routes are disabled.

Run the retrieval evaluation from `backend/` with `python evaluate_retrieval.py`. The included five-query benchmark is synthetic and should be treated as a regression check, not proof of real-world accuracy.

## Agent investigation API

Send a POST request to `/agents/investigate` with a question and a scenario object. The workflow retrieves supporting notes, calls the deterministic simulation, prepares domain findings and runs basic output checks. It returns an execution trace and evidence IDs. The agents are explicit Python components in this milestone, not LLM-driven autonomous agents.

## Repository layout

```text
backend/
  app/
    knowledge/ seeded knowledge documents and hybrid retriever
    models/    typed request/response models
    services/  city simulation and knowledge query logic
  tests/      automated tests
  main.py
  requirements.txt
  pytest.ini
  pyproject.toml
```

## Run locally (when ready)

Requires Python 3.11+.

```bash
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

Run tests with:

```bash
cd backend
python -m pytest
```

## Milestone 4 changes

- Added bounded document chunking and a local persistent JSON store.
- Added ingestion, listing and deletion endpoints.
- Added input validation, reserved built-in IDs, duplicate detection and document-count limits.
- Added a retrieval evaluation script and end-to-end ingestion/query/delete test.
- Current backend test suite: 22 passing tests in the development environment.

## Important limitations

- The city and all initial inputs are synthetic, not live municipal data.
- Results are simplified scenario estimates, not engineering-grade forecasts.
- The simulation uses deterministic formulas; the knowledge engine uses BM25 + TF-IDF retrieval and extractive responses. No model training or generative LLM is claimed in this milestone.
- No autonomous action is sent to real city infrastructure.

## Interactive frontend (Milestone 3)

The `frontend/` directory contains a static Three.js city interface with five selectable districts, a rotating 3D city model, district profiles, scenario controls, and a knowledge query panel. The frontend calls the FastAPI endpoints for scenario simulation and knowledge search. The district labels and baseline populations are aligned to the backend's synthetic dataset.

To preview the interface, open `frontend/index.html` in a modern WebGL-enabled browser with internet access (Three.js is loaded from jsDelivr). To use simulation and knowledge search, start the backend as described above. The frontend is not a production deployment, and GitHub Pages can host only the static frontend; the Python API requires a separate running backend.

A GitHub Pages workflow is included at `.github/workflows/pages.yml`. It will publish the frontend after the repository is pushed to `main` and Pages is enabled in repository settings.

## Optional local AI generation (Milestone 5)

The agent workflow now supports optional local text generation through Ollama. It is disabled by default and does not require a paid API. See `backend/.env.example` and `docs/architecture.md` for configuration and limitations. Numeric simulations remain deterministic Python calculations; the local model can only draft an explanation and recommendation. If the local model is unavailable, the system falls back to its deterministic response.

Validation in the development environment: **25 backend tests passed**. Live Ollama inference was not tested because no local Ollama server/model was available in that environment.

## Optional neural retrieval and reranking (Milestone 6)

The knowledge engine now has optional adapters for Sentence Transformers embeddings and a CrossEncoder reranker. They are deliberately disabled by default: the app does not download model files automatically, and the standard-library BM25 + TF-IDF path remains available offline. To enable neural retrieval, install the optional package `sentence-transformers`, make the chosen model available locally, and set `LIFEOS_EMBEDDINGS=on`. To enable reranking, also set `LIFEOS_RERANKER=on`. Model names can be overridden with `LIFEOS_EMBEDDING_MODEL` and `LIFEOS_RERANKER_MODEL`. The `/knowledge/status` endpoint reports which retrieval components actually loaded.

Neural retrieval combines lexical and semantic scores; optional reranking scores a bounded set of candidates. Returned sources include the first-stage retrieval score, final score, and whether reranking ran. Missing packages or model files fall back to lexical retrieval. No neural model was downloaded or live-inference-tested in this development environment.

Milestone 6 validation: **28 backend tests passed**. The five-query synthetic retrieval regression benchmark reported Hit Rate@1 = 1.00, Hit Rate@3 = 1.00 and MRR = 1.00. This is a small regression set, not a real-world accuracy claim.

## Milestone 8 — Frontend/backend integration

The dashboard now uses the backend's canonical district identifiers (`CENTRAL`, `NORTH`, `EAST`, `SOUTH`, `WEST`) and reads the city population from `/city`. The scenario studio renders the API's nested traffic, water, and electricity metric objects. The knowledge panel displays retrieved source IDs and the retrieval caveat. A new Agent Command Centre calls `/agents/investigate` and displays the plan, specialist findings, execution trace, evidence IDs, LLM status, and mechanical verification result.

### Verification performed

- Backend test suite: 35 tests passed.
- Frontend JavaScript syntax check: passed with Node.js `--check`.
- Integration tests cover investigation workflow, knowledge ingest/query/delete, and frontend/API district and endpoint contract alignment.

### Known limitations

- The browser UI has not been exercised in a real graphical browser in this environment; visual layout and WebGL behavior still need browser-level testing.
- The frontend uses a configurable API URL. GitHub Pages alone cannot host the FastAPI backend.
- Ollama inference and optional neural embedding/reranking models have not been live-tested here.
- City data and simulation coefficients are synthetic and are not validated forecasts.

## Milestone 9 — Reliability and API safety

- Added a configurable CORS origin allowlist through `LIFEOS_CORS_ORIGINS`.
- Added a 1 MB request-body limit and clear handling for invalid `Content-Length` headers.
- Added baseline response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Cache-Control`.
- Expanded automated API tests for these safeguards.

For a hosted frontend, set `LIFEOS_CORS_ORIGINS` to its exact origin(s), separated by commas. The `*` default is intended for local prototyping only; do not use it as a production security boundary. This prototype does not yet include user authentication, authorization, or abuse-rate limiting and should not be exposed publicly as a production backend.

## Milestone 10 — Scenario intelligence and history

- Added a local JSON-backed scenario history with atomic file replacement and a 100-record retention cap.
- Added endpoints to save, list, retrieve, and delete named scenarios.
- Added multi-scenario comparison for traffic, water, and electricity projections (2–5 saved scenarios per comparison).
- Added CSV export with formula-injection protection for user-supplied scenario names.
- Added frontend controls to save scenarios, view history, select scenarios for comparison, delete saved entries, and export history.
- History is stored in `backend/data/scenarios.json` by default. Set `LIFEOS_SCENARIO_STORE` to choose another path. Runtime history is excluded from source archives by `.gitignore`.

### Milestone 10 verification

- Backend tests: 44 passed.
- Python compilation: passed.
- Frontend JavaScript syntax check: passed.
- Scenario comparisons use the exact saved deterministic outputs; they do not introduce predictive AI or real municipal data.

## Milestone 11 — Decision reports

- Download a PDF report for an individual saved scenario at `GET /scenarios/{scenario_id}/report.pdf`.
- Download a side-by-side PDF comparison for 2–5 saved scenarios at `POST /scenarios/compare/report.pdf`.
- Reports include scenario inputs, deterministic projected indicators, model assumptions, retrieved knowledge references where available, and explicit synthetic-data limitations.
- The dashboard exposes individual report links and a comparison PDF action.
- PDF generation uses ReportLab; install it from `backend/requirements.txt`.

Reports are decision-support summaries for the fictional Nova City model. They are not validated planning advice for real infrastructure.

## Milestone 12: Authentication and workspaces

Added account registration/login, signed expiring bearer tokens, PBKDF2 password
hashing, and SQLite-backed user-isolated scenario/document workspaces. See
[`docs/authentication-and-workspaces.md`](docs/authentication-and-workspaces.md)
for endpoint details and security limitations. The frontend is not yet wired to
these authenticated workspace endpoints; legacy demo endpoints remain shared.

Before deployment, set a strong `LIFEOS_AUTH_SECRET` and a private persistent
`LIFEOS_WORKSPACE_DB`. The development signing secret is not safe for production.

## Milestone 13 — Frontend authentication

- Added sign-in and account registration gate to the web interface.
- Added session validation, sign-out and tab-scoped bearer-token handling.
- Connected scenario save, list, delete, comparison and PDF export to the
  authenticated per-user workspace endpoints.
- Added private workspace notes with create/list/delete controls.
- Added owner-checked single-scenario and comparison PDF endpoints.
- Private notes are stored separately but are not yet part of the shared RAG
  index. The older demonstration endpoints remain shared and require hardening
  or removal before a public multi-user deployment.

## Milestone 14 — Workspace isolation and private knowledge retrieval

- Added `POST /workspace/knowledge/query`, which requires a valid bearer token and searches only the authenticated user's saved workspace documents.
- Private retrieval uses a transparent BM25-style lexical score and returns source document IDs, titles, domains, and scores. It does not claim neural embeddings or generative answers.
- Added a private-note search panel to the authenticated frontend.
- Removed user-uploaded notes from the public city knowledge retriever. The public `/knowledge/query` endpoint now searches only the built-in synthetic Nova City documents.
- Disabled legacy shared document ingestion/deletion and shared scenario history/report endpoints with HTTP 410 responses. Authenticated workspace endpoints are the supported path for personal data.
- Added tests for unauthenticated access, user-to-user retrieval isolation, private source attribution, and disabled shared-storage routes.

### Milestone 14 verification

- Backend tests: 51 passed.
- Python compilation: passed.
- Frontend JavaScript syntax check: passed.
- Private workspace search was tested through two separate test accounts; one account could not retrieve the other's note.

### Remaining security limitations

This is a prototype hardening step, not a production security certification. Before public deployment, add login rate limiting, account recovery, stronger session/token lifecycle controls, HTTPS, a deployment-specific secret, persistent database backups, and an external security review. Public synthetic city simulation and investigation endpoints remain unauthenticated and should be rate-limited before public exposure.

## Milestone 15 — Authenticated private agent investigations

- Added `POST /workspace/agents/investigate`, protected by the existing bearer-token authentication.
- The investigation workflow now accepts an explicit knowledge source override. The private route searches only the signed-in user's workspace documents and passes those sources to the decision workflow; it does not query the public city corpus.
- Private evidence IDs are checked against the retrieved source set rather than assuming public `NOVA-*` identifiers. An investigation with no matching private notes can still calculate the deterministic scenario, but it reports no private evidence.
- Added a private agent investigation panel to the authenticated workspace UI, including district and population-change controls, execution trace, verification state and private evidence IDs.
- Added tests for authentication, per-user evidence isolation, no-evidence behavior and frontend wiring.

This remains a deterministic prototype. Private note retrieval uses lexical matching; it is not semantic understanding or a production security certification.

## Milestone 16 — Intent-aware planning and stronger verification

- Added deterministic question classification for compare, explain, risk-assessment, and general scenario requests.
- Added explicit domain focus detection for traffic, water, and energy while retaining cross-domain checks.
- Expanded the tool registry with declared inputs, outputs, read-only status, and allowed data scopes.
- Added deterministic topological ordering and dependency-cycle rejection for the agent task graph.
- Strengthened verification to check finite/non-negative baseline and projected metrics, finite percentage outputs, exact deterministic recalculation, evidence source structure, evidence-ID matching, and plan integrity.
- Added planner metadata, selected-tool details, ordered task plans, and individual verification results to investigation responses.
- Updated both public and private investigation panels to display intent, focus domains, task plans, verification checks, and execution traces.

### Milestone 16 validation

- Backend tests: **58 passed**.
- Python compilation: passed.
- Frontend JavaScript syntax check (`node --check`): passed.
- Five-query retrieval regression: Hit Rate@1 = 1.00, Hit Rate@3 = 1.00, MRR = 1.00. This small synthetic benchmark is a regression check, not evidence of real-world retrieval accuracy.
- Browser visual testing, live Ollama inference, optional neural model inference, and production security review were not performed.

The verifier checks internal consistency and evidence formatting. It does not prove that a source document is factually correct or that synthetic simulation assumptions match a real city.

## Milestone 23 — Predictive intelligence and forecasting

- Added `POST /forecasts/project` with a validated 1–10 year horizon and separate annual growth assumptions for traffic, water, and electricity.
- Added transparent compound-growth projections from the existing deterministic scenario output, including a Year 0 reference row and yearly metric values.
- Added a Forecast Explorer to the Scenario Studio. It uses the selected district and population-change setting and lets users adjust each annual rate and the forecast horizon.
- Added validation and regression tests for compound growth, zero and negative growth, deterministic results, invalid horizons/rates, unknown districts, and API behavior.
- Clearly labels the feature as an assumption-based projection, not a trained predictive model or real-world forecast.

See [Milestone 23 forecasting documentation](docs/predictive-forecasting.md) for the formula and limitations.

## Live external data (Milestone 24)

The backend now has an optional Open-Meteo current-weather connector. Users must
enter coordinates and request a snapshot; external weather is displayed with
provider attribution and timestamps. It is not blended into the synthetic city
infrastructure model. See `docs/external-data-integration.md` for API details,
source limitations and test coverage. No external call is made on page load.
