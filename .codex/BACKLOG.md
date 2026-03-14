# Backlog

## P0
- Reconcile `handover.md` with the actual repo contents.
- Confirm whether missing scaffold files should be recreated here.
- Verify the real CashClaw API routes and payloads.
- Create the adapter package skeleton under `src/cashclaw_adapter/`.
- Add basic tests and local developer tooling.

## P1
- Implement health, create task, and get task flows end to end.
- Add structured logging and upstream error mapping.
- Add Memgraph bootstrap and write paths.
- Add approval proposal models and endpoints.

## P2
- Add task listing, messaging, and cancel flows.
- Add graph-backed search for promoted learnings.
- Add CI, linting, and type checking.
- Add auth if the adapter is ever exposed beyond localhost.

## Definition of done for the first meaningful milestone
- Real CashClaw API contract is verified.
- Adapter package exists and runs locally.
- `GET /health`, `POST /tasks`, and `GET /tasks/{task_id}` work.
- Durable task or payment-related writes land in Memgraph.
- Tests cover happy-path and key failure-path behavior.

## Session checklist
- Confirm repo reality before assuming files exist.
- Make one vertical slice work before widening scope.
- Update `DECISIONS.md` if a durable choice changes.
- Update `WORKLOG.md` with what changed, what remains, and blockers.
