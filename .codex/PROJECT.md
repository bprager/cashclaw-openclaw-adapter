# Project Snapshot

## Repo status
This repository is currently a planning scaffold, not a working adapter implementation.

Files present today:
- `README.md`
- `pyproject.toml`
- `handover.md`

Notably absent right now:
- `src/`
- `scripts/`
- tests
- Docker or systemd files mentioned in the handover

Treat `handover.md` as design intent, not as proof that the code already exists.

## Goal
Build `cashclaw-openclaw-adapter`, an adapter between:
- OpenClaw as orchestrator
- CashClaw as external worker
- Memgraph on host `odin` as shared durable graph

## Current truth sources
- `handover.md`: best source for intended architecture and backlog
- `pyproject.toml`: current Python package metadata and dependency intent
- actual filesystem: source of truth for what exists now

## Constraints
- Keep CashClaw as a separate process.
- Keep Memgraph for durable shared facts, not transient chatter.
- Do not store secrets in Memgraph.
- OpenClaw should remain the approval gate for external side effects.

## Dependencies already declared
- `fastapi`
- `uvicorn[standard]`
- `requests`
- `pydantic`
- `pydantic-settings`
- `gqlalchemy`

These dependencies imply the intended implementation stack even though the source tree is not present yet.

## Immediate reality check
Before writing integration code, confirm:
- the real CashClaw API surface
- the expected adapter package layout
- whether the missing scaffold should be recreated here or pulled from another source

## Useful starting point for future sessions
If implementation begins from this repo state, the likely first structure will be:
- `src/cashclaw_adapter/app.py`
- `src/cashclaw_adapter/config.py`
- `src/cashclaw_adapter/models.py`
- `src/cashclaw_adapter/memgraph.py`
- `src/cashclaw_adapter/cashclaw_client.py`
- `tests/`
- `scripts/bootstrap_memgraph.cypher`
