# MCP Tool Performance Classification

Production readiness guide for Frontend Perception MCP tools. **Optimize for engineering value, not benchmark scores.**

## Performance philosophy

| Workflow | Priority | Latency guidance |
|----------|----------|------------------|
| Very frequent tools (health, verify, resolve_*) | Latency first | <2s warm |
| Browser observation | Rich evidence once; trim serialization | 2–5s observe OK |
| Component search / integrate | Match quality first | 3–5s search OK; integrate plan 3–8s |
| Development SEO | Usefulness first; partial OK | 2–5s budget; `ok:true` partial on timeout |
| Professional SEO | Async background | Enqueue <500ms; poll |

## Classification tiers

| Tier | Meaning | Agent expectation |
|------|---------|-------------------|
| **Fast** | <2s warm, <5s cold | Safe in every interactive loop |
| **Needs optimization** | 2–10s or large payloads | Use lightweight flags; cache when possible |
| **Background only** | >10s or external OAuth/crawl | Never block; poll or defer |
| **Candidate for redesign** | Duplicates host-agent work or unreliable | Prefer host reasoning + thin MCP probe |

## Core browser loop (Fast)

| Tool | Warm | Notes |
|------|------|-------|
| `perception_health` | <100ms | No browser |
| `perception_session_start` | 1–3s | Browser boot — amortize across session |
| `perception_navigate` | <1s | URL only |
| `perception_observe` | 1–4s | Default `detail=summary_only`; use `metadata_only` / `no_images` to cut payload |
| `perception_navigate_and_observe` | 2–5s | Same budget flags as observe |
| `perception_verify` | 1–3s | Required after ACT |
| `perception_diff` | <500ms | Scan registry only |
| `perception_execute_script` | <2s | Page-bound |
| `perception_execute_actions` | 1–4s | Bounded action list |

**Payload budget:** `summary_only` (default) omits DOM; `metadata_only` drops images; `full` for deep DOM reads only.

## Resolvers (Fast)

All `perception_resolve_*` and `perception_validate_*` tools: **<2s** via sync offload thread pool. Deterministic graph/code reads — do not duplicate in host agent.

## SEO Intelligence

| Tool | Tier | Target |
|------|------|--------|
| `perception_seo_audit_start` (development) | Fast | 2–5s inline; requires `scan_id`; returns `partial` with recommendations if budget exceeded |
| `perception_seo_audit_start` (professional) | Background only | <500ms enqueue → poll |
| `perception_seo_audit_poll` | Fast | <200ms |
| `perception_seo_connect` | Background only | OAuth — user-paced |
| `perception_seo_audit` (legacy) | Background only | Scripts only; blocks up to 90s |
| `perception_seo_query` | Fast | Graph read |
| `perception_seo_verify` | Needs optimization | Re-audit subset |

**Localhost** auto-selects development mode (browser + AI visibility only).

## Component Intelligence

| Tool | Tier | Target |
|------|------|--------|
| `perception_search_components` | Needs optimization | 2–5s acceptable for better registry coverage (12 registries default) |
| `perception_select_component_foundation` | Needs optimization | Parallel guidance; bounded candidates |
| `perception_integrate_component` | Fast (plan_only default) | 3–8s plan; partial plan on timeout; never 60s block |
| `perception_integrate_component` (execute_install) | Background only | Explicit user intent only |

**Cache:** `.cache/shadcn_catalogs/` — warmed at MCP startup via `warm_shadcn_catalog_cache()`.

## Design / workflow probes

| Tool | Tier | Notes |
|------|------|-------|
| `perception_probe_form` | Fast | Single form |
| `perception_probe_guards` | Fast | **Session hygiene:** restores URL by default; reports `session_hygiene` |
| `perception_flow_describe` | Fast | Checkpoints only — agent runs verify |

## Heavy / background tools

| Tool | Tier | Notes |
|------|------|-------|
| `perception_code_context` | Needs optimization | 30s cap; sync offload |
| `perception_inspiration_discover` | Background only | External sites |
| `perception_audit_*` | Background only | Lighthouse subprocess |
| `perception_figma_*` | Needs optimization | Network-bound |

## MCP resources

| Resource | Tier | Notes |
|----------|------|-------|
| `perception://agent-guide` | Fast | Static markdown, in-memory cache |
| `perception://resolver-guide` | Fast | Same |
| `perception://seo-guide` | Fast | Same |

## Philosophy checklist

1. **Host agent reasons; MCP proves.** Avoid LLM calls inside MCP except optional Bedrock post-validation.
2. **Default to lightweight.** `summary_only`, `plan_only`, development SEO.
3. **Never surprise session state.** Restore URL after guard probes unless `restore_session=false`.
4. **Partial > blocking.** Timeouts return degraded partial results with next actions.
5. **Measure cold vs warm.** Catalog cache and scan registry make warm paths the common case.

## Optimization backlog

- Parallel Lighthouse in professional SEO (already parallel provider collect)
- Font search HTTP 400 hardening
- `design_lint` IndexError edge case
- Further DOM truncation in `apply_observation_budget` for `full` mode
