# EXP-025 Scorecard (live)

**App / URL:** Arm A = PrimeStay / flow-craft `http://127.0.0.1:5174`; Arm B = Pulse Maze `http://localhost:5173`  
**Date:** 2026-07-18  
**Agent model / chat:** Cursor agent; Arm A = historical [PrimeStay feedback report](file:///c:/Users/usman/Downloads/frontend-flow-craft-main/frontend-mcp-feedback-report.md); Arm B = this session with §2b active (`sess_bc549feff47d`)

## Arm A (control) — current rule only

| ID | Result | Notes |
|----|--------|-------|
| S1 | FAIL | Early inspiration_discover once; mockup match never paid snapshot / SpecDiff (schema only) |
| S2 | PASS | plan_component_search → select_component_foundation paid for redesign |
| S3 | PASS | Multiple verifies with `data.verified=true` |
| S4 | FAIL | Mockup phase tunneled Observe/Verify; Design family barely used while reference unpaid |
| S6 | FAIL | Opacity “−30%” false-green (overlay wash); soft criteria early |

Families called (order): Session → Inspiration (discover) → Component → Observe/Verify → (mockup) Observe/Verify → execute_script; Design snapshot/SpecDiff/ship skipped

## Arm B (treatment) — agent-brain contract

| ID | Result | Notes |
|----|--------|-------|
| S1 | PASS | Inspiration collect timed out 60s → supersede with `build_design_snapshot(bind_as_reference)` (advancement_eligible) |
| S2 | PASS | plan_component_search + select_component_foundation; portfolio paid `component` |
| S3 | PASS | Section `form:0` verify with JS asserts + brand text → `data.verified=true` |
| S4 | PASS | Paid ≥2 structural families while unpaid ≥2: observe → snapshot → component → verify |
| S5 | PASS | MCP complexity delta = 0 (rule + methodology only; no new owed gates) |
| S6 | PASS | Hard JS/DOM criteria; no soft “looks professional” claim; did not claim UI rewrite done |

Families called (order): health → session_start → inspiration_collect (fail/timeout) → navigate_and_observe → build_design_snapshot → plan_component_search → select_component_foundation → verify(section)

**Owed plan (brain, ≤3):** inspiration|snapshot → component → observe/verify — executed without tunneling on singular `gate.next` alone.

**Caveat:** Arm B is a **coordination-behavior probe** on Maze login (redesign intent), not a full landing rewrite like Arm A. Hypothesis under test is host family discipline, not visual quality of a finished redesign.

## Verdict

- Winner: **B**
- Keep simple MCP + agent brain? **Y**
- Next: **freeze B** — no new portfolio claim gates; optional later: card `owed[]` hint only if hosts still tunnel without §2b
