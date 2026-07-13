# Local Validation — v1.1.2 (pre-publish)

**Date:** 2026-07-13  
**Method:** Local `src/` handlers + pytest + `run_polish_eval` (NOT installed PyPI MCP)

## Development SEO — root cause fixed

| Phase | Before fix | After fix |
|-------|------------|-----------|
| `probe_connections` (all 6 providers) | **2,729ms** | — |
| `probe_connections` (development, browser only) | — | **0.2ms** |
| `development_audit` | ~2,800ms+ (timeout risk) | **369ms** |
| `handle_seo_audit_start` | timeout at 3s exec layer | **343ms** |

**Bottleneck:** Development mode probed LibreCrawl/GSC/Lighthouse connection status (HTTP) before planning, even though only `browser` is used.

**Fixes (not timeout-only):**
- Development mode probes **browser only**; other providers default to `not_configured`
- Skip `snapshot_diff` in development mode
- Compact graph JSON on development save path

**Execution timeout:** Restored to **4s** (sufficient with real work completing in <400ms).

## Integrate component

| Metric | Value | Budget |
|--------|-------|--------|
| `integrate_component` plan_only (polish eval) | 3,229ms | Handler 5s / exec 8s |
| Search quality | 100 candidates, table + sortable hits | 12 registries |

Handler timeout **5s plan / 10s execute** — justified by search + foundation selection + doc read (3s cap with fallback). Execution runtime **8s** (not 15s).

## Quality verification

| Optimization | Evidence collected? | Quality impact |
|--------------|--------------------|----------------|
| `summary_only` default | **Yes** — `collect_observation()` runs fully; only response omits `observation` dict | None |
| Browser SEO normalize | Full scan observation → evidence refs | None |
| Dev SEO skip CRG | Heuristic codebase hints only (fast glob) | Acceptable for dev; pro gets CRG |
| Component `max_registries=12` | More registry coverage | Improved vs v1.1.1 |
| MCP `read_resource` fix | N/A locally | Resources work when published |

## Local test results

```
pytest (seo, component, stdio, coordination): 39 passed
run_polish_eval: ok=true
  seo_audit_start_development: 343ms, status=completed
  search_components_warm: 216ms
  integrate_component: 3229ms
  probe_guards: restored=true
  mcp_static_resources: ok (handler layer)
```

## Not done yet (per user request)

- [ ] Build + publish new package
- [ ] Install from PyPI
- [ ] Restart Cursor MCP
- [ ] End-user evaluation on **installed MCP only**
