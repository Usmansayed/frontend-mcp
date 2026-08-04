# Guide Lab — Production readiness scorecard (Option C)

**Date:** 2026-07-18  
**Harness:** `python -m navigation.guide_lab.runner` + `pytest tests/guide_lab tests/test_methodology_resources.py`

## Isolated quiz packs

| Pack | Cases | Arm A | Arm B |
|------|------:|------:|------:|
| Base Q01–Q24 | 24 | — | — |
| Hard H01–H24 | 24 | — | — |
| Production P01–P32 | 32 | — | — |
| **Total** | **80** | **3/80 (4%)** | **80/80 (100%)** |

Production themes covered: empty unpaid, sticky design, figma reference, residue/sections ladder, forms/guards, SEO bait, wrong-port mockup, opacity wash, ship-before-snapshot, resolve owners.

## Contract tests

`tests/guide_lab/test_production_guides.py` + methodology resources:

- All `perception://guide/*` structured  
- Hard-fails P0 coverage  
- Always-on short (≤550 words) + binding keywords  
- `.mdc` ↔ CLI rule sync  
- Empty unpaid → class min path  
- Sticky polish keeps ship  

**Result: 21 passed**

## Production verdict

Option C dual guides are **quiz- and contract-validated** for production semantics.  
Remaining ops step: **republish/reinstall** so installed MCP serves `perception://guide/*` (Cursor always-on already updated).
