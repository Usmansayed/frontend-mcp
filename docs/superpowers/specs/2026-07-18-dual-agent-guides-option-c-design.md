# Dual Agent Guides (Option C) — Design

**Date:** 2026-07-18  
**Status:** Implemented (Option C dual guides)  
**Research:** `docs/superpowers/research/2026-07-18-agent-guide-redesign/`

## Decision

**C — Dual surface**

| Surface | Content |
|---------|---------|
| Always-on rule (Cursor + CLI) | Ultra-short: apply? → scoreboard loop → hard fails → Done one-liner → which card to read |
| Methodology `perception://guide/*` | Situation cards (greenfield, redesign/mockup, feature, hotfix/polish, forms) + scoreboard + hard-fails |
| Existing `perception://*-workflow` | Deep reference only (unchanged intent) |

MCP coordination stays facts-only; no new unpaid claim gates.

## Test plan

1. Guide Lab policy pack Q+H → B ≥ 95%  
2. `tests/test_methodology_resources.py` includes new guide URIs  
3. Guide Lab MCP catalog serves clean arm  

## Promote

Always-on + methodology land together in this change (user approved implement).
