# EXP-018 — Surface thin / thin-clear on host + agent_summary

**Date:** 2026-07-18  
**Status:** done  
**Track:** evidence quality  
**Constraint:** No new Coordination gates.

## Hypothesis

EXP-017 put honesty in the ledger, but agents read `host_action` / `agent_summary` first. Thin snapshot and thin-clear ship stayed invisible.

## Change

- `compile_engineering_strategy` appends `EVIDENCE THIN` / `EVIDENCE DEGRADED` / `SHIP THIN-CLEAR` to `host_action`
- Strategy field `evidence_quality_alerts` + `surface_engineering_strategy` copies into `agent_summary`
- Snapshot / ship MCP handlers expose `evidence_quality` / `thin_clear` in advisory

## Lab lock

- `scenarios/host_surfaces_thin_snapshot.yaml`
- `scenarios/host_surfaces_thin_clear_ship.yaml`

## Verdict

**Win.** Honesty is now on the surfaces agents already read.
