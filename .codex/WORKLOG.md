# Work Log

## 2026-03-14

### What changed
- Created the initial `.codex/` markdown kit for shared project context.
- Added repo-specific notes instead of generic templates.
- Documented the mismatch between `handover.md` and the actual filesystem.
- Built the first adapter scaffold under `src/cashclaw_adapter/`.
- Added the initial FastAPI endpoints, placeholder CashClaw client, and Memgraph task writes.
- Added tests, coverage enforcement, Ruff, mypy, and Markdown linting.

### Current state
- The repo now has a runnable phase-one implementation slice.
- `make check` passes with 29 tests and 95.11% coverage.
- The real CashClaw API contract is still unverified and remains the main source of risk.

### Next good move
- Inspect the real CashClaw API surface and replace the placeholder request and response mapping.
- Extend tests first as each real route or payload shape is introduced.

### Notes for the next session
- Read `.codex/PROJECT.md` first for the repo reality check.
- The filesystem now confirms the basic scaffold, but `handover.md` still overstates what was
  already present before this session.
- Keep this log short and append-only.
