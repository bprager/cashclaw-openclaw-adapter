# Status

## Overall
Project phase: phase-one scaffold implemented

Current confidence: medium on architecture intent, medium on implementation readiness

## Summary
The repository now contains a runnable first implementation slice of the adapter, including
the package scaffold, FastAPI endpoints, settings, a placeholder CashClaw client, Memgraph task
upserts, tests, coverage enforcement, type checking, Ruff, and Markdown linting.

The intended direction is clear:
- OpenClaw orchestrates
- CashClaw executes as a separate process
- Memgraph on `odin` stores durable shared graph data

The CashClaw contract has now been verified against the upstream repository for the currently
available dashboard routes: `/api/setup/status`, `/api/status`, and `/api/tasks`.

The main remaining integration gap is that CashClaw's local API does not expose task creation,
so adapter `POST /tasks` remains intentionally unimplemented.

## Completed
- Created `src/cashclaw_adapter/` with app, config, models, CashClaw client, and Memgraph store.
- Implemented `GET /health`, `GET /tasks`, and `GET /tasks/{task_id}` against the real CashClaw task-monitoring API.
- Kept `POST /tasks` explicit with `501 Not Implemented` because upstream task creation is not available.
- Added startup dependency validation, localhost gating, logging, and upstream error mapping.
- Added `scripts/bootstrap_memgraph.cypher` and `.env.example`.
- Added pytest coverage enforcement with a project threshold above 90%.
- Added Ruff, mypy, and Markdown linting commands.
- Verified the current scaffold at 95.25% test coverage.

## In progress
- Richer persistence for task events, pricing, and workflow metadata is still minimal.

## Blockers
- CashClaw's local HTTP API does not expose task creation.
- Memgraph writes are still limited to task upserts for the initial vertical slice.
- Approval proposal endpoints are not implemented yet.

## Next milestone
Build on the verified monitoring contract by adding richer task/event persistence and deciding
how OpenClaw should initiate work when CashClaw itself does not expose a create-task endpoint.

## Recommended next step
Design the adapter's task-submission strategy around a real upstream entrypoint rather than the
old placeholder `POST /api/tasks` assumption, then extend tests before adding new routes.

## Update template
When status changes, update these sections:
- `Overall`
- `Summary`
- `Completed`
- `In progress`
- `Blockers`
- `Next milestone`
- `Recommended next step`
