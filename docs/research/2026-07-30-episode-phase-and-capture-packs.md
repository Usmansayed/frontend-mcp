# Research + plan: Episode phases + parallel visual packs

**Date:** 2026-07-30  
**Target version:** `1.2.0.dev62`  
**Status:** Implement now

## Decisions

1. **Narrow runtime state** — expose `card.phase` ∈  
   `intent | flow | layout | sections | components | verify | ship`  
   Derived from face class + unpaid pack + claim_extra. **Not** the 150-state research leaves.

2. **Multi-view visuals** — reuse existing `capture_design_evidence` (viewport + full + section crops).  
   Extend `perception_observe` / `navigate_and_observe` with `screenshot_pack` / `focus_sections` / `max_sections`.  
   Sequential on one primary browser (flight lock). No default multi-Chromium.

3. **Live regions** — if no snapshot regions, probe DOM semantic tags via JS so section crops still work.

4. **Intel parallelism** — raise prefetch hard budget; keep creative kit category fan-out; card.phase guides what to warm.

## Non-goals

- Local LLM inside MCP  
- 15 host agents  
- Isolated browser pool (env-gated later if metrics demand)

## Exit criteria

- `card.phase` present on face card  
- Observe with `screenshot_pack=design` returns multiple labeled images  
- Prefetch budget tunable; tests green  
