# Inspiration production harden — ship notes

**Date:** 2026-07-27  
**Scope:** technical gaps only (coordination / “use inspiration for most tasks” deferred)

## Shipped

| Gap | Fix |
|-----|-----|
| HTTP connection reuse | `browser/http_pool.py` — shared httpx.Client; `http_get` / Serper prefer pool, urllib fallback |
| Chromium leak on timeout | `live_capture._default_capture` cancels task + `force_kill()` / `SessionStore.reset_browser` |
| Region crop | `region_focus.py` + `screenshot_url(focus_scope=)` CDP clip for chrome/component/section |
| DDG-only quality | Alias retry, loose-link parse fallback, never cache empty SERPs; stronger component query craft |
| Pulse / widen MCP | `perception_inspiration_pulse` (light, no live SS), `perception_inspiration_widen` (bump one level) |

## Explicitly deferred (next)

- How agents use inspiration for **most** tasks
- Coordination layer requiring look-lock on structural greenfield
- Design VF `vs_inspiration` when refs bound
- Durable multi-replica SERP/affinity stores

## Verification

- `tests/test_inspiration_production_harden.py` + related — pass
- `scripts/hardcore_inspiration_battery.py` — re-run after ship
