# Perfect Coordination Layer — Phase B Design (Unified Episode Readout)

**Date:** 2026-07-18  
**Status:** Approved (charter A→B) — implementing  
**Depends on:** Phase A (`coordinator_card.v1`, fingerprint skip)

---

## Goal

One agent-facing object: `agent_summary.episode_card` (`episode_card.v1`) so hosts need not dig `data.coordinator` + full strategy + alerts separately.

## Contract

`episode_card.v1` = Phase A coordinator card fields **plus**:

| Field | Source |
|-------|--------|
| `schema` | `episode_card.v1` |
| `what_matters` | First `what_matters_now` line, else `host_action` |
| `surface_type` | strategy |
| `influence_level` | strategy |

`data.coordinator` remains `coordinator_card.v1` (unchanged).  
`data.episode_card` mirrors `agent_summary.episode_card` for envelope consumers.

## Non-goals

No new gates, no route-level backlog, no payload size regressions beyond the single card.
