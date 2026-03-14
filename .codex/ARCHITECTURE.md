# Architecture Intent

## System roles
- OpenClaw orchestrates tasks and approvals.
- CashClaw executes work as a separate external worker.
- Memgraph stores durable shared graph data on host `odin`.

## Boundaries to preserve
- Do not embed CashClaw into OpenClaw internals as a first step.
- Do not use Memgraph as a dump for every transient event.
- Do not store secrets in Memgraph.
- Normalize metrics, wallet, quote, payment, and knowledge data before persistence.

## Intended adapter responsibilities
- expose a local HTTP API for OpenClaw
- translate adapter requests into real CashClaw API calls
- validate and normalize payloads
- persist durable graph state into Memgraph
- gate risky or irreversible actions behind approval proposals

## Intended early endpoints
- `GET /health`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/{task_id}/approval-proposals`
- `GET /tasks/{task_id}/approval-proposals`
- `POST /approval-proposals/{proposal_id}/decision`

## Intended graph entities
- `Agent`
- `Session`
- `Project`
- `Task`
- `TaskMetric`
- `Wallet`
- `Quote`
- `Payment`
- `KnowledgeEntry`

## Relationship intent
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

## Biggest known risk
The assumed CashClaw contract in `handover.md` has not been verified against a real implementation. That is the highest-confidence place future breakage will come from.

## Recommended implementation order
1. Verify the real CashClaw API contract.
2. Build the thin FastAPI surface for health and task operations.
3. Add Memgraph writes for durable state.
4. Add error mapping, logging, timeouts, and startup checks.
5. Add approval proposal endpoints.
6. Add tests before broadening the API surface.
