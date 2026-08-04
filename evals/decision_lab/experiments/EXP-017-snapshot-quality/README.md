# EXP-017 — Snapshot `coordination_evidence.quality`

**Date:** 2026-07-18  
**Status:** done  
**Track:** evidence quality  
**Constraint:** No new Coordination gates — enrich ledger quality only.

## Hypothesis

Agents treat snapshot `ok` as “dense measured draft.” Empty `quality={}` hid thin/degraded captures.

## Change

`normalize._snapshot_evidence_quality` fills ledger quality from `snapshot_summary` / layout / coverage / revision gate. Advancement still follows transport + blocking (not thinness).

Also enriched (same pass, no gates):

- Inspiration quality: profiles + seed unresolved + bind readiness  
- Ship/review quality: coverage_checks, thin_clear, delta tops  

## Lab lock

`scenarios/snapshot_quality_payload.yaml` — dense snapshot advances with nonempty quality; thin fixture sets `thin: true` while still `succeeded`.

## Verdict

**Win.** Agents can read thin vs useful without a new gate.
