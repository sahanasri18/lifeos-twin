# Authentication and personal workspaces (Milestone 12)

LifeOS Twin now includes a standard-library authentication and workspace API.
It uses SQLite for account/workspace persistence, PBKDF2-HMAC-SHA256 password
hashing (310,000 iterations), signed HMAC bearer tokens, and ownership checks on
workspace reads/deletes.

## Endpoints

- `POST /auth/register` — create an account and return a 12-hour bearer token.
- `POST /auth/login` — verify credentials and return a token.
- `GET /auth/me` — return the authenticated account.
- `GET /auth/status` — report whether the development signing secret is active.
- `POST /workspace/scenarios`, `GET /workspace/scenarios`,
  `DELETE /workspace/scenarios/{id}` — private scenario history.
- `POST /workspace/documents`, `GET /workspace/documents`,
  `DELETE /workspace/documents/{id}` — private document metadata and ownership.

Send `Authorization: Bearer <access_token>` to every `/workspace/*` endpoint.

## Configuration

Set `LIFEOS_AUTH_SECRET` to a long random value before deployment. The built-in
secret exists only to make local development and automated tests easy; it is
not safe for a public deployment. Set `LIFEOS_WORKSPACE_DB` to a persistent,
private SQLite path. Back up this database securely. Do not commit it.

## Security boundaries and known gaps

- Passwords are never stored in plain text.
- Tokens are signed, expire after 12 hours, and are checked against an existing
  account on each request. There is no refresh-token or revocation list yet.
- Workspace scenario and document records are scoped by authenticated user ID.
- Legacy demo endpoints such as `/scenarios` and `/knowledge/*` remain shared
  prototype endpoints and are **not** converted to account-private storage in
  this milestone. Do not expose those legacy endpoints as private user data in
  a public deployment.
- Login/register rate limiting, email verification, password reset, MFA,
  CSRF protection for cookie auth, database encryption at rest, and a security
  review are not implemented.
- The current frontend is not yet wired to the login/workspace APIs. The API
  contract is available for the next integration milestone.

This is a development foundation, not a production security certification.

## Frontend integration (Milestone 13)

The browser UI now provides a sign-in / registration gate, validates an existing
session with `GET /auth/me`, and keeps the bearer token in `sessionStorage` for
the current browser tab. Signing out clears the token and hides workspace data.

Scenario save/list/delete and individual/comparison PDF exports use the
`/workspace/*` routes and bearer authentication. The frontend comparison is
calculated from scenarios returned for the signed-in account. Private notes use
the authenticated workspace document endpoints. Notes are currently private
storage records only; they are **not** yet indexed by the shared RAG retrieval
engine.

The old demonstration `/scenarios` and shared `/knowledge/*` endpoints remain
available for prototype/demo workflows and are not account-scoped. Do not
present those endpoints as private multi-user data. Before public deployment,
restrict or remove shared write endpoints, configure `LIFEOS_AUTH_SECRET` with a
strong random secret, enforce HTTPS, add login rate limiting and password
recovery, and complete a security review. The current browser token is exposed
to same-origin JavaScript through session storage, so preventing XSS remains
important.

## Private knowledge search (Milestone 14)

`POST /workspace/knowledge/query` requires a bearer token and searches only documents owned by the authenticated user. Results include the private document ID, title, domain, text, and lexical score. The current implementation is BM25-style lexical retrieval; it is not neural semantic search and does not use an LLM to generate answers.

The public `/knowledge/query` endpoint now indexes only built-in synthetic Nova City documents. User-uploaded notes are not added to that shared index. Legacy shared document ingestion/deletion and shared scenario history/report routes return HTTP 410 and direct clients to the authenticated workspace routes.

## Private agent investigations (Milestone 15)

`POST /workspace/agents/investigate` requires the same bearer token as other
workspace routes. It runs the existing deterministic planner and city
simulation, but retrieves supporting documents only through the authenticated
user ID. The private sources are passed directly into the investigation
workflow; the public Nova City corpus is not queried by this route.

The response includes `knowledge_scope: "private_workspace"`, the private
`evidence_ids`, and a `knowledge_caveat`. If no private note matches, the
simulation still runs, but the response clearly reports that there is no
private document evidence. This endpoint does not make the simulation itself
personalized from notes; notes provide supporting context, while numeric
outputs remain deterministic and based on the submitted scenario.
