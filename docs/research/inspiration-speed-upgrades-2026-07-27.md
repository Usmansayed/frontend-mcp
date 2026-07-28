# Inspiration speed & reliability upgrades — ship notes

**Date:** 2026-07-27  
**Implements:** research follow-ups P0–P1 from Ask session

## Shipped

| Upgrade | What |
|---------|------|
| **Overlap web + multi-scout** | When pattern pack is thin, `asyncio.gather(web_inspire, multi_scout)` so wall ≈ max |
| **SERP cache** | 15m TTL on `search_web` results (`serp_cache.py`) |
| **Preview HEAD validate** | Drop dead OG URLs; trusted daisy/Webflow CDN skipped; fail-open if all drop |
| **Sticky source affinity** | Remember winning providers per scope/intent ~30m; boost specialist order + scout categories |
| **Wide/max variety soft-stop** | Keep hunting until `soft_stop_refs` (not just `min_refs`); cascade continues after early scout |
| **Usable pack floor** | `min_refs = soft_stop // 2` (no hard cap at 3) so standard page packs soft-stop at 4 |

## Files

- `preview_validate.py`, `serp_cache.py`, `source_affinity.py`
- Wired in `collect.py`, `web_search.py`, `web_inspire.py`, `pattern_acquire.py`

## Verification

- Unit: `tests/test_inspiration_speed_upgrades.py` (+ related) — pass
- Live: `scripts/hardcore_inspiration_battery.py` — **13/13** (~12s wall)

## Still open

- ~~httpx connection pool~~ → shipped (`http_pool.py`)
- ~~`inspiration_pulse` / widen MCP split~~ → shipped
- ~~Chromium force-close on cancel~~ → shipped
- ~~Region crop for live screenshots~~ → shipped
- **Next (product):** use inspiration for most tasks + coordination look-lock spine
