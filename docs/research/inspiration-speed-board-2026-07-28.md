# Inspiration speed board — Phases A–E

**Date:** 2026-07-28  
**Script:** `scripts/eval_inspiration_speed_board.py`  
**Raw:** `docs/research/inspiration_speed_board.json`

## Verdict: **BOARD PASS** (A–E)

| Gate | Target | Result |
|------|--------|--------|
| A cold p50 | ≤ 3.0s | **0.002s** (max 1.15s) PASS |
| A warm p50 | ≤ 1.5s | **0.34s** PASS |
| B parallel ×3 | ≤ 5.0s | **0.81s** PASS |
| B sequential ×5 | ≤ 12s | **1.00s** PASS |
| C quality @ speed | 6/6 budgets | **p50 1.22s / max 2.94s** PASS |
| D cache ×3 | warm ≤0.4s or ≥3× | **warm p50 0.002s (~500×)** PASS |
| E no Stealthy | friendly CDN path | **budget untouched** PASS |

### Phase C — quality under hard walls

| Case | Budget | Wall | Hits | Providers |
|------|--------|------|------|-----------|
| forms/login | ≤8s | **2.94s** | 8 | daisyui, saasframe_login |
| forms/checkout | ≤8s | **0.09s** | 8 | daisyui, saasframe_checkout |
| chrome/text_input | ≤6s | **1.95s** | 8 | daisyui, saasframe_login |
| section/hero | ≤8s | **0.96s** | 6 | daisyui, hero_gallery |
| section/footer | ≤5s | **0.14s** | 4 | daisyui, footer_design |
| chrome/button | ≤6s | **1.49s** | 8 | aceternity, daisyui, ibelick |

### Phase D — cache / repeatability

| Mode | Result |
|------|--------|
| Seed (cache fill) | **0.997s**, 4 hits |
| Warm cache ×2 | **p50 0.002s**, `cache_hit=true` |
| Pool-only ×3 (cache off) | **p50 0.76s**, still ≥3 hits |

**Fix shipped:** result-cache now short-circuits **before** pattern HTTP (warm path was still paying saasframe/etc.).

### Phase E — failure routing

| Check | Result |
|-------|--------|
| Friendly CDNs deny Stealthy | saasframe / daisyui / hero / footer |
| WAF host remains eligible | dribbble (policy only; not in p50) |
| Live light landing | 4 hits / 0.33s; Stealthy budget **2→2** |

## Cuts shipped

1. Pattern soft-stop for **section + page** (specialist hits only, not web).  
2. Soft-stop **skips gallery cascade + web** (`skip_cascade`).  
3. Pattern path runs for **page/landing** (specialists before Channel C).  
4. **Light** does not force multi-scout.  
5. **Light** strips **Behance** from HTTP cascade (no Stealthy cold tax).  
6. Speed board honors level web defaults (no forced Channel C on light).  
7. **Result cache before pattern** — warm MCP retries skip specialist HTTP.
