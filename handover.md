# Handover for Codex

## Goal
Continue the `cashclaw-openclaw-adapter` skeleton into a working integration between:
- **OpenClaw** as orchestrator
- **CashClaw** as external worker
- **Memgraph** on host `odin` as shared durable graph

This repo is a **scaffold**, not a finished integration.

## Current status
The repo already contains:
- FastAPI adapter service
- Pydantic models for task, metrics, payment, and learning promotion payloads
- Memgraph Cypher upserts for tasks, metrics, wallet, quote, payment, and knowledge entries
- basic health endpoint
- Docker, systemd, and env skeletons

Primary files:
- `src/cashclaw_adapter/app.py`
- `src/cashclaw_adapter/config.py`
- `src/cashclaw_adapter/models.py`
- `src/cashclaw_adapter/memgraph.py`
- `src/cashclaw_adapter/cashclaw_client.py`
- `scripts/bootstrap_memgraph.cypher`

## Important architecture decisions already made
1. **CashClaw stays a separate process**. Do not try to embed it into OpenClaw session internals first.
2. **Memgraph on `odin` is the shared graph** for durable cross-run facts.
3. **Do not store secrets in Memgraph**.
4. **Wallet/task metrics may be shared**, but only in normalized form.
5. **OpenClaw remains the approval gate** for external side effects.

## Biggest current gap
The adapter currently assumes a placeholder CashClaw API contract:
- `GET /api/health`
- `POST /api/tasks`
- `GET /api/tasks/{task_id}`

That payload shape is **not verified against the real CashClaw implementation** yet.

This is the first thing to fix.

## What Codex should do first
### 1. Inspect real CashClaw API surface
Find the real routes and request/response shapes in CashClaw.
Focus especially on:
- health/status endpoint
- create task endpoint
- get task endpoint
- task status model
- task message / cancel / revise endpoints, if present
- any metrics, wallet, quote, or payment related endpoints

Then update:
- `src/cashclaw_adapter/cashclaw_client.py`
- `src/cashclaw_adapter/app.py`
- `README.md`

### 2. Add robust adapter-side error handling
Current code is too thin.
Needed improvements:
- structured exception mapping for upstream CashClaw errors
- request timeouts configurable via env
- clear 4xx vs 5xx separation
- logging
- retries only where safe
- startup validation for Memgraph and CashClaw reachability

### 3. Add approval proposal endpoints
We want support for operations that should not execute automatically.
Add endpoints and data model for proposals such as:
- submit quote
- send external client message
- submit final work
- destructive or irreversible actions

Recommended shape:
- `POST /tasks/{task_id}/approval-proposals`
- `GET /tasks/{task_id}/approval-proposals`
- `POST /approval-proposals/{proposal_id}/decision`

Write proposal state into Memgraph.

### 4. Add tests
There are no tests yet.
Minimum:
- model validation tests
- Memgraph query parameter tests
- FastAPI endpoint tests with mocked CashClaw client
- health endpoint tests
- task submission happy path and failure path tests

## Suggested immediate backlog
### P0
- verify real CashClaw API and patch payloads
- add logging
- add tests
- make `/health` more explicit
- ensure Memgraph bootstrap script is sufficient for your Memgraph version

### P1
- add approval proposal model and endpoints
- add `GET /tasks` passthrough or graph-backed listing
- add `POST /tasks/{task_id}/message`
- add `POST /tasks/{task_id}/cancel`
- add graph search endpoint for promoted learnings

### P2
- add auth for adapter if it is ever exposed off localhost
- add OpenTelemetry or structured logs
- add `Makefile`
- add CI workflow
- add mypy/ruff/pytest

## Assumptions that may need correction
- `odin` is reachable from the adapter host at Memgraph port `7687`
- CashClaw exposes an HTTP API locally
- OpenClaw will call this adapter over localhost
- quote/payment data will be written into Memgraph by the adapter, not pulled from Memgraph first
- `gqlalchemy` is acceptable for the Memgraph connection layer

## Known weaknesses in current code
### `app.py`
- no logger
- no response models
- no startup checks
- no pagination or listing endpoints
- no approval workflow

### `cashclaw_client.py`
- no typed client
- no retry policy
- no mapping of upstream errors
- assumes JSON responses everywhere

### `memgraph.py`
- Cypher is inline, okay for now, but could be split into query modules later
- no read queries yet for graph search, listing, or analytics
- no protection against writing null-heavy noisy metrics repeatedly

### `README.md`
- documents setup, but not the unresolved CashClaw API contract risk strongly enough
- needs examples once actual payload shapes are known

## Recommended implementation details
### Logging
Add standard structured logging early. Keep it simple.
At minimum log:
- request id
- endpoint
- task id
- upstream CashClaw URL/path
- Memgraph write success/failure

### Config
Extend env config with:
- `CASHCLAW_TIMEOUT_SEC`
- `CASHCLAW_CONNECT_TIMEOUT_SEC`
- `LOG_LEVEL`
- `ADAPTER_REQUIRE_LOCALHOST` or equivalent

### Tests
Use:
- `pytest`
- `httpx` test client or FastAPI test client
- monkeypatch or mocks for CashClaw

### Code quality
Add:
- `ruff`
- `mypy`
- `pytest`

## Graph model intent
Durable graph entities currently intended:
- `Agent`
- `Session`
- `Project`
- `Task`
- `TaskMetric`
- `Wallet`
- `Quote`
- `Payment`
- `KnowledgeEntry`

Current relationship intent:
- `(:Session)-[:REQUESTED]->(:Task)`
- `(:Task)-[:BELONGS_TO]->(:Project)`
- `(:Task)-[:DELEGATED_BY]->(:Agent)`
- `(:Task)-[:EXECUTED_BY]->(:Agent)`
- `(:Task)-[:HAS_METRIC]->(:TaskMetric)`
- `(:Task)-[:GENERATED]->(:Quote)`
- `(:Task)-[:RESULTED_IN]->(:Payment)`
- `(:Agent)-[:USES]->(:Wallet)`
- `(:Wallet)-[:RECORDED]->(:Payment)`
- `(:KnowledgeEntry)-[:DERIVED_FROM]->(:Task)`

Do **not** turn Memgraph into a dump for every transient event.
Keep ephemeral runtime chatter local to CashClaw.

## Commands likely useful to the next agent
### Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn cashclaw_adapter.app:app --host 127.0.0.1 --port 8787
```

### Health check
```bash
curl http://127.0.0.1:8787/health
```

### Bootstrap Memgraph
```bash
# run scripts/bootstrap_memgraph.cypher against Memgraph on odin
```

## Strong recommendation
Before building more features, verify the real CashClaw routes and payloads. Right now that is the main source of likely breakage.

## Definition of done for the next meaningful milestone
A good next milestone would be:
1. real CashClaw API integrated
2. health, submit task, get task working end to end
3. task metrics and payment writes landing in Memgraph
4. tests present
5. approval proposal flow stubbed and persisted

## Final note
This repo was generated from a design discussion. It is intentionally opinionated:
- OpenClaw orchestrates
- CashClaw executes
- Memgraph on `odin` stores durable shared knowledge and normalized economics

Keep that boundary intact unless there is a very strong reason to collapse it.

