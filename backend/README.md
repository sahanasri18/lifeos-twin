
## Milestone 17 — Controlled task execution engine

- Added a dependency-aware task executor that dispatches explicit Python handlers for context retrieval, deterministic simulation, three specialist analyses, decision preparation, and verification.
- Task handlers receive only the outputs of their declared dependencies; results are recorded by task ID.
- Failed tasks are recorded, dependent tasks are skipped, and independent tasks can continue. Invalid plans are rejected before execution.
- Investigation responses now include an execution run summary and per-task records (status, dependency IDs, registered tool, duration, output keys, and any bounded error message).
- Public and private investigation panels display task completion, failures, skipped tasks, and per-task execution details. Private investigations preserve the authenticated user's private knowledge scope.
- Planning remains deterministic and rule-based. This is a controlled execution engine, not an autonomous LLM planner; the optional local model still only drafts the final explanation/recommendation.

### Milestone 17 validation

- Backend tests: 64 passed.
- Python compilation: passed.
- Frontend JavaScript syntax check: passed.
- ZIP integrity: passed.
- No browser visual test, Ollama inference, neural model inference, or production security review was performed.


## Milestone 18 — Private agent memory

Private workspace investigations can be stored as account-scoped history. Related prior investigations are retrieved by transparent lexical overlap with a same-district boost. The API exposes `GET /workspace/agents/memories` and `DELETE /workspace/agents/memories/{memory_id}`. The investigation request accepts `remember: false` to opt out of saving. Memory records are historical context only: they are not evidence documents, do not train a model, and do not change simulation calculations.

## Milestone 20: specialist debate

Investigation responses now include `specialist_debate`: three deterministic domain specialists score all four alternatives, record domain preferences and challenges, and produce a transparent vote-based consensus with dissent. The `specialist_debate_consensus_valid` verification check validates the returned consensus. See `../docs/multi-agent-debate.md` for the method and limitations. These are rule-based Python components, not autonomous LLM agents.

## Forecasting endpoint (Milestone 23)

`POST /forecasts/project` accepts a `scenario`, `years` (1–10), and annual growth assumptions for traffic, water, and electricity (each -20% to +50%). It returns Year 0 through the requested horizon using compound growth. The rates are user-supplied assumptions; this is not a trained model or real-world forecast. See `../docs/predictive-forecasting.md`.

## External data connector (Milestone 24)

- `GET /data-sources` lists connected public providers and scope.
- `POST /data-sources/open-meteo/current` accepts user-supplied latitude and
  longitude and returns an attributed current-weather snapshot.
- External provider failures return 502; invalid coordinates return 422.
- Weather is contextual only and is not used in synthetic infrastructure
  calculations. See `../docs/external-data-integration.md`.
