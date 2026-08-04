# EXP-019 — SpecDiff delta tops + revision honesty

**Date:** 2026-07-18  
**Status:** done  
**Track:** evidence quality  
**Constraint:** No new Coordination gates — quality + host honesty only.

## Hypothesis

Agents ignore SpecDiff because ledger quality lacked delta tops / soft-seed skips, and host never said `SPECDIFF REVISION` / `SPECDIFF SOFT-SEED`.

## Change

- `_specdiff_quality_fields` on snapshot + design_review ledger quality (`delta_top_ids`, drift counts, `soft_seed_partial`)
- Host / `evidence_quality_alerts` surface `SPECDIFF REVISION` and `SPECDIFF SOFT-SEED`
- MCP snapshot/review advisories mirror the same strings

Advancement rules unchanged (revision_required does **not** force provisional by itself).

## Lab lock

- `scenarios/specdiff_revision_host.yaml`
- `scenarios/specdiff_soft_seed_honesty.yaml`

## Verdict

**Win.** SpecDiff honesty is visible on ledger + host.
