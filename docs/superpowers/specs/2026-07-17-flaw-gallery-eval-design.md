# Hidden-Flaw Coordination Eval (Flaw Gallery)

**Date:** 2026-07-17  
**Status:** Approved — approach 1, pack C (catch rate + decision quality)

## Goal

Fewer, denser cases that plant **hidden** UI flaws and score whether the coordination stack:

1. **Catches** the flaw (catch rate)
2. Catches it in the **right layer** — Verify conventions vs Ship Council (decision quality)
3. Keeps **claim-done blocked** until the right gates clear

Used in fix loops: change product → re-run gallery → compare scorecards.

## Architecture

```
sandbox /eval/flaws/<case_id>   → intentional DOM/CSS flaws
evals/flaw_gallery/cases/*.yaml → expectation cards
scripts/run_flaw_gallery.py     → session → observe → snapshot → soft verify
                                  → (optional) ship mode → scorecard JSON
```

## Case pack (v1)

| ID | Flaw | Must layer |
|----|------|------------|
| F1 | Sidebar position static | verify |
| F2 | Subtle horizontal overflow | verify |
| F3 | Equal-weight KPI cluster | ship |
| F4 | Narrow centered main shell | ship |
| F5 | Sticky on wrong child; chrome still scrolls | verify |
| F6 | Soft-text pass + chrome fail + hierarchy issue | both |

## Scorecard fields (per case)

- `catch_ok` — required signal/assertion fired
- `layer_ok` — verify vs ship as expected
- `claim_blocked_ok` — claim_complete prohibited when expected
- `soft_verify` — actual `data.verified`
- `ship_signals` — challenge signal ids
- `host_action` snippet
- `tools_used`

Suite pass = all cases `catch_ok && layer_ok && claim_blocked_ok`.

## Non-goals (v1)

- Full Done-ladder agent simulation
- Snapshot-only fixtures (add later if CI too slow)
- Subjective brand challenges
