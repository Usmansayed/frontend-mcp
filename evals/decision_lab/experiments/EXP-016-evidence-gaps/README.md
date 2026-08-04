# EXP-016 — Characterize evidence value gaps

**Date:** 2026-07-18  
**Status:** done (characterization)  
**Track:** evidence quality  
**Hypothesis:** Agents under-use MCP because evidence payloads are thin — not because Coordination lacks gates.

## Method

Code + Decision Lab probe of Inspiration / Snapshot / Design Review / SpecDiff → `coordination_evidence` / `agent_summary`.

## Findings

| Family | Weak spot | Agent impact |
|--------|-----------|--------------|
| Snapshot | `ok` → succeeded with **empty `quality={}`** | Cannot tell thin vs dense measured draft |
| Inspiration | quality is only blob counts; seed Spec always provisional | “3 images” looks done while geometry unresolved |
| SpecDiff | revision gate skips many seed partials; delta not in ledger quality | Agents ignore drifts |
| Ship | thin coverage can still clear with low confidence buried | “Ship clear” over-trusted |
| Review mode | no explicit `coordination_evidence.quality` | Findings stay English-only |

## Desired (no new gates)

1. Snapshot ledger `quality` carries coverage / degraded / revision flags  
2. Inspiration `quality` carries profiles + unresolved geometry counts  
3. Ship/review `quality` carries coverage_checks + delta tops  
4. Lab scenarios lock these payloads  

## Verdict

**Characterization win.** First implementation: EXP-017 snapshot quality enrichment.

## Next

EXP-017 — populate snapshot `coordination_evidence.quality` in normalize (+ lab lock).
