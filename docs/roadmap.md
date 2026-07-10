# Roadmap

Status key: ✅ shipped · 🚧 in progress · 📋 planned · ⏸ deferred

## v0.2.0 — Visual delivery (✅ shipped)

- Inline `ImageContent` on observe / verify-fail / diff
- Annotated screenshots, element/full viewport modes
- `visual_insights` (overflow, overlaps, zero-size clickables)
- Visual diff (side-by-side + heatmap)
- PyPI: `frontend-perception-engine` + `frontend-mcp` alias

## v0.3 — Documentation & reference foundation (🚧)

- `references/browser-tools-mcp` clone for study
- `docs/` architecture, roadmap, tool reference, feature docs
- Module migration plan (no big-bang refactor)

## v0.4 — Console module (✅ shipped)

- [x] `navigation/console/` — CDP Runtime + Log ring buffer
- [x] Session-scoped console history from `perception_session_start`
- [x] Filters by level / substring via `perception_console_get`
- [x] Structured `console` section in `agent_summary` + observation
- [x] `perception_console_clear`
- [x] Contract tests + `tests/test_console_buffer.py`

## v0.5 — Network module (✅ shipped)

- [x] `navigation/network/` — CDP Network capture + `loadingFinished`
- [x] Request/response headers, size-capped bodies via `Network.getResponseBody`
- [x] HAR 1.2 export per scan (`artifacts/.../network/{name}.har`)
- [x] Slow (1000ms) + duplicate (2s window) detection
- [x] API grouping + GraphQL `operationName` heuristic
- [x] `perception_network_get` / `perception_network_clear`
- [x] `perception://scan/{id}/network.har` resource
- [x] Contract + unit tests

## v0.6 — Audits (✅ shipped)

- [x] `navigation/audits/` — Lighthouse CLI runner + LHR parser
- [x] `perception_audit_accessibility` / `performance` / `seo` / `best_practices`
- [x] Structured `AuditReport` with score, warnings, blocking, metrics
- [x] Artifacts: `artifacts/{session}/audits/lighthouse-{category}.json`
- [x] Unit + contract tests (skips if Node/Lighthouse unavailable)

## v0.7 — Reports & diagnosis (✅ shipped)

- [x] `navigation/reports/` — `PerceptionReport` model, hints, markdown renderer
- [x] `perception_full_diagnosis` — observe + console + network + a11y/perf audits
- [x] `perception_audit_mode` — all four Lighthouse categories
- [x] `perception_debug_mode` — observe + console + network (no audits)
- [x] Artifacts: `diagnosis.json`, `diagnosis.md`, scan resources
- [x] Unit + contract tests

## v1.0 — Framework Intelligence (✅ shipped)

- [x] `navigation/framework_intelligence/` — detector, cache, Grounded Docs adapter
- [x] `perception_detect_framework` / `perception_framework_docs`

## v1.1 — Seven-module platform layout (✅ shipped)

- [x] Restructure `src/navigation/` into 7 intelligence modules + `core/`
- [x] Move console, network, audits, reports → `frontend_quality_intelligence/`
- [x] Move observe/verify/browser → `visual_browser_intelligence/`
- [x] Move codeGraph → `codebase_intelligence/graph/`
- [x] Move flows/state → `design_workflow_intelligence/`
- [x] Move probes → `component_intelligence/`
- [x] Move visual heuristics → `design_sense_intelligence/`
- [x] Backward-compatible import shims (`perception/`, `console/`, etc.)
- [x] [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md)

## v1.2 — Framework Intelligence + Grounded Docs (✅ shipped)

- [x] Replace Context7 with Grounded Docs MCP adapter
- [x] `DocumentationProvider` abstraction + cross-platform CLI reliability
- [x] On-demand doc scrape/search, normalized `FrameworkKnowledgeResponse`

## v1.3 — Eight-module platform + Consistency Intelligence scaffold (🚧)

- [x] Add `consistency_intelligence/` as 8th module (scaffold only)
- [x] Architecture docs: Design Sense vs Consistency boundary
- [x] [features/consistency_intelligence.md](./features/consistency_intelligence.md)
- [ ] Design token extraction from code + computed styles
- [ ] Spacing / typography / color scale validators
- [ ] `perception_consistency_audit` MCP tool
- [ ] Consistency scoring + regression diff vs prior scan

## v2.2 — Design Sense Intelligence orchestration (🚧 scaffold)

- [x] Module architecture: providers, reviewers, rules, workflows
- [x] Open Design adapter (`OD_DAEMON_URL`) — only direct external integration
- [x] Design Lint rule engine port for DOM/CSS computed styles
- [x] Microsoft review workflow + UICrit rubric pipeline (methodology)
- [x] Crit/Rams specialist reviewer + coordinator pattern
- [x] Architecture v1 frozen: knowledge/, reasoning/, objective/subjective lanes, learning/, pattern_library
- [ ] MCP: `perception_design_review`, `perception_design_critique_region`
- [ ] Wire observe/verify → ReviewRequest enrichment
- [ ] Deep Open Design artifact comparison
- [ ] Contrast/motion deterministic checks

## v2.1 — Component Intelligence orchestrator (✅ contract-driven)

- [x] Phase 1: search planner, multi-pass search, provider merge
- [x] Stable contracts v1.0 (`contracts/` + per-module `contract.py`)
- [x] Structured guidance from all intelligence modules (no fixed % weights)
- [x] `guidance/synthesis.py` — merge module opinions with priority rules
- [x] Split `IntegrationPipeline`: docs → plan → deps → compat → install → adapt
- [x] `plan_executor.py`, `fix_applier.py` — structured execution (dry-run default)
- [x] Repair loop consults all modules via contracts
- [x] MCP: `perception_select_component_foundation`, `perception_integrate_component`
- [ ] Live `execute_install` + provider `install()` for shadcn
- [ ] Browser validation → `perception_observe` / `perception_verify`
- [ ] Deterministic file patches in repair loop and component adapter

## v2.0 — Component Intelligence search engine (✅ Phase 1)

- [x] Query parser with extensible style/type lexicon
- [x] Provider manager + parallel search
- [x] Shadcn registry ecosystem provider (Group A)
- [x] External provider placeholders (Group B)
- [x] Normalized `ComponentCandidate` schema
- [x] `perception_search_components` MCP tool
- [ ] Ranking, project matching, adaptation, installation (later phases)

- [ ] Border radius, shadows, layout grid rules
- [ ] Component + interaction-state consistency checks
- [ ] Visual hierarchy + responsive consistency
- [ ] Fix suggestions (rule-based; no LLM in server)
- [ ] Optional auto-apply patches via host agent workflow

## v0.8 — Browser attach mode (📋)

- [ ] `perception_session_start` with `cdp_url` / attach to user Chrome
- [ ] Document security implications
- ⏸ Not a replacement for managed sessions — optional dev convenience

## v0.9 — Package layout migration (📋)

- [ ] Move subsystems into target folders per `architecture.md`
- [ ] Keep `navigation.mcp` import paths stable (re-export shims)
- [ ] CI: contract tests + phase runners unchanged

## Backlog

- Multi-viewport observe pack (desktop + mobile contact sheet)
- Plugin registry for custom probes
- Bundle `AGENT_GUIDE.md` in wheel (fix PyPI resource path)
- MCP stdio smoke test in CI
- Next.js-specific audit prompts (like BrowserTools, but our schema)

## Explicitly not doing

- Shipping BrowserTools Chrome extension
- Running `browser-tools-server` as dependency
- LLM inside MCP server for "suggested fixes" text generation
- Replacing host agent with autonomous Browser Use as primary path

## How to update this file

When a PR ships a roadmap item, move it to a version section with ✅ and link the feature doc.
