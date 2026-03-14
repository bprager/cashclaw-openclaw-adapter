# Decisions

## Confirmed

### Keep CashClaw separate
CashClaw should remain a separate process rather than being folded into OpenClaw internals early.

### Use Memgraph for durable shared facts
Memgraph on `odin` is the intended shared graph for cross-run durable state.

### Keep approvals in OpenClaw
External side effects should stay gated by OpenClaw rather than executing blindly from the adapter.

### Prefer normalized graph writes
Metrics, wallet, quote, payment, and knowledge data should be written in normalized form, not as raw event dumps.

## Observed repo reality

### The implementation scaffold is missing
`handover.md` references source files and scripts that do not exist in this checkout as of 2026-03-14.

Implication:
Future sessions should verify whether the scaffold needs to be generated here or restored from another source before coding against those paths.

## Open questions
- Where is the real CashClaw API definition or source repo?
- Should the missing adapter scaffold be created manually in this repo?
- Is `gqlalchemy` still the desired Memgraph client once implementation begins?
- What auth model, if any, will be required for non-local deployments?

## Decision log template
Use this format for new entries:

```md
### Short title
Date: YYYY-MM-DD

Decision:
- one or two lines

Why:
- one or two lines

Impact:
- one or two lines
```
