# Coordination perfection program — design

**Date:** 2026-07-28  
**Branch:** `exp/agent-face-simple` (merged to `coordination-sandbox`)  
**Order:** card correctness → agent obedience → end-to-end reliability

## Goal

Make the coordination **agent face** trustworthy enough that following `agent_summary.card` is the correct, complete, non-hanging path for every situation class — proven by adversarial unit tests, no-guide harness, then live Cursor A/B, then latency/soak boards.

“Perfect” here means: **no known P0/P1 face failure modes remain**, with a regression board that stays green.

## Non-goals (this program)

- Rewriting the full PSM / portfolio brain
- Shrinking the ~73-tool catalog (card trust is the mitigation)
- Inspiration provider perfection beyond “does not hang the face”

## Phase 1 — Card correctness (NOW)

**Pass bar:** All adversarial face unit tests green; no-guide E2E BOARD 4/4; P0 gaps G1–G3 closed; P1 matrix locked or explicitly deferred with ticket.

| ID | Failure | Fix intent |
|----|---------|------------|
| G1 | Done-state re-spines forever | When verify passed + no `claim_extra`, `next=""` (claim if `claim_ok`) |
| G2 | `claim_ok` ignores `claim_extra` | `claim_ok` false whenever `claim_extra` non-empty |
| G3 | Polish → greenfield full ladder | Classify polish/chrome cues (+ tier) as `hotfix` before design_driven |
| G4–G12 | Feature/mockup/sections/spec/VF | Adversarial unit matrix (fix or document) |

**Evidence artifacts:** `tests/test_coordinator_card.py`, `scripts/eval_agent_face_no_guide_e2e.py`, this doc + research note.

## Phase 2 — Agent obedience

**Pass bar:** Human A/B runbook (`docs/research/agent-face-human-ab-runbook.md`) — simple face wins on adherence + false-green vs prior long-guide behavior; no UI quality loss.

Automate what we can (discoverability harness); remainder is live Cursor.

## Phase 3 — End-to-end reliability

**Pass bar:** Session boards finish with `data.verified=true`, no false-green, inspiration/select timeouts bounded; latency SLO documented and met on BOARD classes.

## Done ladder for the program

1. Phase 1 board green → bump `dev49`  
2. Phase 2 human A/B pass → candidate release note  
3. Phase 3 soak green → non-dev tag consideration  

## Open decisions

- Done sentinel: empty `next` string (not a fake tool name) when episode is claimable/complete.
- Polish remains spine `hotfix` (no separate `spine/polish`).
