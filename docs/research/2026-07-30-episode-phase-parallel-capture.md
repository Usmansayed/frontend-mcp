# Research + Plan: Episode Phase + Parallel Visual Packs

**Date:** 2026-07-30  
**Target version:** `1.2.0.dev62`  
**Status:** Implemented (dev62)

## Goals

1. Narrow agent decisions with an explicit **`card.phase`** (not 150 leaf states).
2. Make observe return **multi-view visuals in one call** (viewport + full + sections).
3. Push **more server-side parallel intel** (prefetch budgets / medium band) without parallelizing the primary browser.

## Research findings

| Need | Existing asset | Gap |
|------|----------------|-----|
| Multi-shot visuals | `capture_design_evidence` (VF / design tools) | Observe uses single `screenshot_mode` only |
| Section crops | Snapshot `layout.regions` | Observe may lack snapshot — need live region probe |
| Parallel browser tools | Flight lock (serial) | Correct for one Chromium; same-page multi-shot is sequential |
| Parallel intel | Episode prefetch + creative kit gather | Raise budgets; allow medium-band warm for design classes |
| Decision narrowing | Face × pack × band | Add **phase** enum on card |

## Design decisions

1. **Phase** = compile-time enum from face + unpaid + claim_extra. Never leaf state IDs.
2. **Capture pack on observe** reuses `capture_design_evidence`; `screenshot_pack=auto` → `design` for greenfield/redesign/mockup sessions, else viewport; explicit `design` always multi-view.
3. **Live regions** via page JS probe when no snapshot regions (best-effort).
4. **No multi-Chromium by default** — isolated browsers stay env-gated.
5. **Prefetch:** hard budget default 8s; heavy+ unchanged; medium greenfield/redesign warms creative_kit + light inspiration scout.

## Exit criteria

- `card.phase` present on face card tests
- Observe with `screenshot_pack=design` attaches multiple labeled images
- Prefetch tests still green; VERSION bumped
