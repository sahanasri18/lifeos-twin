# LifeOS Twin — Architecture Notes

## Approved initial product direction

A fictional city digital twin combining a visual city interface, deterministic simulation, evidence-backed retrieval, and specialist agents that explain and compare possible interventions.

## Build sequence

1. **Simulation foundation (current):** synthetic city model, traffic/water/electricity calculations, API, tests.
2. **Knowledge engine:** document ingestion, searchable chunks, citations, evaluation set. Start with local, free components; no external paid API.
3. **Agent workflow:** coordinator, domain analysts, simulation caller, and verifier. Agents must call deterministic tools for numeric outputs; they must not invent figures.
4. **3D frontend:** browser-based city scene and scenario controls. Build only after API contracts are stable.
5. **Integration and evaluation:** end-to-end tests, retrieval quality checks, failure handling, reproducible demo.
6. **Deployment:** separate final approval and deployment review.

## Safety and trust rules

- Synthetic data must always be labelled as synthetic.
- Every numerical result must be traceable to a simulation function and its assumptions.
- RAG answers must show source references; unsupported claims must be marked as unknown.
- The system is advisory only and cannot control real infrastructure.
- No paid model/API is part of the required path.

## Optional local language model (Milestone 5)

LifeOS Twin can optionally call a locally running Ollama server through its `/api/chat` endpoint. Configure `backend/.env` from `.env.example` and set `LIFEOS_LLM_ENABLED=true`. The default model name is `qwen2.5:3b`, but the model must already be installed in the local Ollama instance. No hosted API key or paid inference service is used.

The model is restricted to drafting a short explanation and recommendation from precomputed simulation outputs and retrieved excerpts. It cannot execute tools, change numeric simulation outputs, or bypass the deterministic verification step. If Ollama is disabled or unavailable, the workflow uses its deterministic recommendation. The `/ai/status` endpoint reports configuration only; it does not test whether Ollama is reachable.

The current development environment did not have an Ollama model server available, so the live model inference path has not been run end-to-end here. Its response parsing, disabled mode, and failure fallback are covered by automated tests.


## Milestone 16 — Planning and verification controls

The question planner is deterministic and rule-based. It labels the request intent, identifies traffic/water/energy focus terms, and creates a seven-task dependency graph. All three specialist checks remain in the plan to preserve cross-domain review. The graph is rejected if it contains duplicate IDs, unknown dependencies, unregistered tools, self-dependencies, or cycles. A stable topological order is returned for inspection.

The tool registry is an allow-list. Each entry declares its purpose, read-only status, input/output fields, and permitted data scope. The registry describes the tools available to the workflow; it does not grant access to arbitrary system commands or external services. Private investigations continue to receive only the signed-in user's retrieved documents.

The verifier checks finite and non-negative baseline/projected metrics, finite percentage outputs, exact agreement with a fresh deterministic simulation calculation, source record structure, one-to-one evidence-ID matching, and task graph validity. Passing these checks means the response is internally consistent. It does not validate source truth, city assumptions, or engineering safety.

## Controlled task execution (Milestone 17)

The validated planner graph is executed by `app.services.task_executor.execute_plan`. The executor accepts the plan, a task-ID-to-handler mapping, and per-investigation context. It validates the graph before running any handler, follows deterministic topological order, and makes completed dependency outputs available to later handlers. Handler exceptions are captured as failed task records; dependent tasks are skipped while independent tasks remain eligible to run. The response exposes task status, dependency IDs, selected registered tool, duration, output keys, and a bounded error string. This execution engine does not dynamically generate code, access arbitrary tools, or grant write access.
