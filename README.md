# cashclaw-openclaw-adapter

Adapter service between OpenClaw, CashClaw, and Memgraph on `odin`.

## Current phase
This repository now contains the first implementation slice of the adapter:
- FastAPI app scaffold
- environment-backed settings
- typed CashClaw client aligned to the real dashboard API
- Memgraph persistence layer for task upserts
- `/health`, `GET /tasks`, and `GET /tasks/{task_id}`
- pytest coverage enforcement and Markdown linting setup

The adapter now tracks the verified CashClaw dashboard routes:
- `GET /api/setup/status`
- `GET /api/status`
- `GET /api/tasks`

CashClaw's local HTTP API does not expose a task-creation endpoint, so adapter `POST /tasks`
currently returns `501 Not Implemented` with a clear explanation instead of pretending that
upstream support exists.

## Project layout
- `src/cashclaw_adapter/app.py`: FastAPI app and error mapping
- `src/cashclaw_adapter/config.py`: settings and environment parsing
- `src/cashclaw_adapter/models.py`: adapter and normalized CashClaw task models
- `src/cashclaw_adapter/cashclaw_client.py`: upstream HTTP client for setup, status, and task list
- `src/cashclaw_adapter/memgraph.py`: durable graph writes
- `scripts/bootstrap_memgraph.cypher`: minimal Memgraph bootstrap
- `tests/`: unit and endpoint tests

## Local setup
1. Create a virtual environment with Python 3.11 or newer.
2. Install the project and dev tooling.
3. Copy `.env.example` to `.env`.

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run the adapter
```bash
uvicorn cashclaw_adapter.app:app --host 127.0.0.1 --port 8787
```

## Quality gates
The project is configured to fail if coverage drops below 90%.

```bash
make check
```

Individual commands:

```bash
make test
make lint
make lint-md
make typecheck
```

## Next milestone
- keep the verified CashClaw contract current with upstream changes
- add richer task and event persistence from `/api/tasks`
- expand Memgraph persistence beyond task nodes
- add approval proposal endpoints
