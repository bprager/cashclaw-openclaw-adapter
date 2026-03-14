# cashclaw-openclaw-adapter

Adapter service between OpenClaw, CashClaw, and Memgraph on `odin`.

## Current phase
This repository now contains the first implementation slice of the adapter:
- FastAPI app scaffold
- environment-backed settings
- typed placeholder CashClaw client
- Memgraph persistence layer for task upserts
- `/health`, `POST /tasks`, and `GET /tasks/{task_id}`
- pytest coverage enforcement and Markdown linting setup

The biggest unresolved risk is unchanged from `handover.md`:
the upstream CashClaw API contract used here is still a placeholder and must be verified against
the real CashClaw implementation.

## Project layout
- `src/cashclaw_adapter/app.py`: FastAPI app and error mapping
- `src/cashclaw_adapter/config.py`: settings and environment parsing
- `src/cashclaw_adapter/models.py`: request and response models
- `src/cashclaw_adapter/cashclaw_client.py`: upstream HTTP client
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
- verify the real CashClaw HTTP contract
- replace placeholder request and response mapping
- expand Memgraph persistence beyond task nodes
- add approval proposal endpoints
