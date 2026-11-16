# Private Agent Memory — Milestone 18

## Purpose

The private agent memory feature lets a signed-in user review related earlier investigations and compare their calculated outcomes with a new run.

## What is stored

Each successful, verified private investigation can store:

- The investigation question and district
- The deterministic scenario result
- The recommendation and specialist findings
- Evidence document IDs (not copied document text)
- The verification outcome and creation time

The memory table is linked to the account record with a foreign key and cascade deletion. Queries and deletions always include the authenticated account ID.

## Retrieval behavior

The service compares question terms using transparent lexical overlap and adds a small score boost when the district matches. It checks the most recent 100 records for the current account and returns at most three matches. This is a simple history lookup, not a trained learning model.

When prior records are found, the API compares their projected traffic, water, and electricity values with the current run. These comparisons are informational only.

## API

- `POST /workspace/agents/investigate`: accepts `remember: false` to skip saving; saving is enabled by default.
- `GET /workspace/agents/memories`: lists the current user's recent memory records.
- `DELETE /workspace/agents/memories/{memory_id}`: deletes one memory owned by the current user.

All three routes require a valid bearer token.

## Boundaries

- Memories are not source evidence and are displayed separately from retrieved documents.
- Memories do not alter simulation calculations or verification results.
- No model is trained or fine-tuned from these records.
- Users can opt out per investigation and delete individual records.
- The feature is local-first and uses the existing SQLite workspace database.
