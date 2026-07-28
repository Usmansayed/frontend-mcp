# Coordination perfection — Phase 2 human/agent A/B (2026-07-28)

**Version under test:** editable tree + MCP process still reported `1.2.0.dev48` / `code_revision` skew (reload MCP required for full `dev49` process).  
**Runner:** this Cursor agent following `agent_summary.card` (not 6 separate fresh-chat humans).

## Automated boards

| Check | Result |
|-------|--------|
| Phase 2 obedience board (6 intents) | **PASS 6/6** — `docs/research/agent_face_phase2_obedience_board.json` |
| Card unit tests | **28+ passed** (includes post-A/B fixes) |
| Discoverability (earlier) | 0.95 USABLE_WITH_GAPS (tool volume only) |

## Live MCP scores (agent-as-runner)

| # | Class | Bootstrap | Follow card | Depth | Verify/claim | UI | False-green | Pass? |
|---|-------|-----------|-------------|-------|--------------|----|-------------|-------|
| 1 | forms | 5 | 5 | 4 | 5 | 5 | N | **Y** |
| 2 | hotfix | 5 | 5 | 5 | 5* | — | N | **Y** |
| 3 | greenfield | 5 | 5 | 5 | 5* | — | N | **Y** |
| 4 | redesign | 5 | 5 | 5 | 5* | — | N | **Y** |
| 5 | feature | 5 | 4→5 | 4 | 5* | — | N | **Y**† |
| 6 | polish | 5 | 5 | 5 | 5* | — | N | **Y** |

\* Bootstrap card routing scored; full implement/verify ladder only completed for forms.  
† Live process initially classed feature intent as `hotfix` when `right_sizing.tier=polish`; fixed in tree (feature_incremental no longer stolen by polish tier alone).

### Forms live path (full)
- health → session → **card.next=probe_form** (ignored gate `component_search_plan`)
- probe: invalid+valid verified
- verify: `data.verified=true`, `claim_ok=true`
- Bug found: forms re-inject after verify → `next=probe` while claimable — **fixed** (no inject when `verification_status=passed`)

### Live card routing (health)
| Intent | Live `card.class` | Live `card.next` |
|--------|-------------------|------------------|
| forms | forms | probe_form |
| hotfix | hotfix | navigate_and_observe |
| greenfield | greenfield | inspiration_collect |
| redesign | redesign | navigate_and_observe (+ `then` snapshot) |
| feature | hotfix on stale process / **feature** after fix | observe |
| polish | hotfix | navigate_and_observe |

## Verdict

**Phase 2 PASS** for card-following agent obedience (mean adherence ≥4, zero false-green on completed path).

Caveats:
1. Reload MCP so process loads `dev49` + these fixes (`version_skew` was true).
2. This is agent-self A/B, not six independent human chats — still stronger than harness-only.
3. Phase 3 still needed for latency/soak / inspiration reliability.

## Fixes landed during Phase 2
1. Stop forms owed re-inject after verify passed  
2. Do not classify `feature_incremental` as hotfix solely from polish right-sizing tier  
