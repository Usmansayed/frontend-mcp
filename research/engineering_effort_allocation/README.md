# Engineering Effort Allocation — Research

**Status:** Research only — not approved for implementation  
**Date:** 2026-07-14

Extends the design-driven coordination proposal with **how much intelligence to spend**, not only **when to intervene**.

## Documents

| Document | Purpose |
|----------|---------|
| [`ENGINEERING_EFFORT_ALLOCATION.md`](ENGINEERING_EFFORT_ALLOCATION.md) | Full research: ROI, Intelligence Budget, EQG, visual impact, diminishing returns, host vs MCP, integration |
| [`diagrams/`](diagrams/) | Mermaid diagrams |

## Core thesis

```text
MCP amplifies the host LLM with deterministic evidence.
Coordinator allocates effort by ROI, not by maximizing tool calls.
```

## Pair with

- Design-driven workflow proposal (when to intervene) — review both before implementation  
- `coordination_layer/research/reports/07_coordination_intelligence_architecture.md`  
- Frozen runtime: `coordination_layer/runtime/` (R0–R11)
