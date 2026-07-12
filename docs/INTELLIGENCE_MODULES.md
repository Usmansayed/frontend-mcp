# Intelligence Modules Architecture

Frontend Perception MCP is organized as **independent intelligence modules** plus a **shared core**. Each module owns its domain and exposes a clean interface; the MCP layer (`navigation/mcp/`) stays thin and delegates to module services.

## Layout

```text
src/navigation/
├── core/                              # Shared infrastructure
├── framework_intelligence/            # 1. Framework detection + docs
├── component_intelligence/            # 2. Component providers + probes
├── design_workflow_intelligence/      # 3. Flows, state, design tools (scaffold)
├── visual_browser_intelligence/       # 4. Browser, observe, verify, visuals (raw collection)
├── design_snapshot_engine/            # 5. Extract → normalize → DesignSnapshot (no critique)
├── design_reference_registry/         # 6. Reference snapshots + structural compare
├── codebase_intelligence/             # 7. CRG graph, code ↔ UI
├── frontend_quality_intelligence/     # 8. Console, network, audits, diagnosis
├── design_sense_intelligence/         # 9. UX reasoning over DesignSnapshot
├── consistency_intelligence/          # 10. Design-system consistency over DesignSnapshot
├── inspiration_intelligence/          # 11. Public inspiration (Dribbble, Behance, …)
├── figma_intelligence/              # 12. User Figma account + design systems (future)
├── resource_intelligence/             # 13. Creative assets (icons, fonts, photos, …)
├── seo_intelligence/                  # 14. SEO orchestration (GSC, GA4, LibreCrawl, …)
├── mcp/                               # MCP protocol (tools, handlers, server)
└── cli/                               # Install wrapper
```

Legacy import paths (`navigation.perception`, `navigation.console`, `navigation.codeGraph`, etc.) remain as **shims** for backward compatibility.

## Module standard structure

Each intelligence module follows this pattern where applicable:

| Layer | Purpose |
|-------|---------|
| `providers/` | External integrations (Grounded Docs, Figma, shadcn, …) |
| `registry.py` | Supported frameworks/tools/services |
| `service.py` | Business logic facade |
| `cache.py` | Module-scoped caching |
| `models.py` | Pydantic/dataclass types |
| `utils.py` | Module helpers |
| `tests/` | Unit tests (repo: `tests/test_<module>.py`) |

MCP tools are registered in `mcp/tools.py` and delegate to module `service.py` via `mcp/handlers.py`.

---

## 1. Framework Intelligence

**Path:** `framework_intelligence/`

Understands the frontend stack and fetches version-aware documentation.

| Capability | Status |
|------------|--------|
| Framework detection | ✅ |
| Version / build tool / package manager | ✅ |
| Project metadata extraction | ✅ |
| Grounded Docs provider (adapter) | ✅ |
| Documentation cache | ✅ |
| Normalized `FrameworkKnowledgeResponse` | ✅ |

**MCP tools:** `perception_detect_framework`, `perception_framework_docs`

See [features/framework_intelligence.md](./features/framework_intelligence.md).

---

## 2. Component Intelligence

**Path:** `component_intelligence/`

Orchestrates **discovery → foundation selection → integration → validation** across all intelligence modules. Not a search engine alone.

| Capability | Status |
|------------|--------|
| Search planner + multi-pass provider search | ✅ |
| Cross-module guidance (framework, codebase, design sense, consistency) | ✅ stable contracts v1.0 (heuristic implementations) |
| Foundation selection (synthesis + priority rules) | ✅ contract-driven |
| Integration pipeline (docs, deps, compatibility, adapter, install) | ✅ orchestrated (dry-run default) |
| Browser validation + repair loop | ✅ contract-driven (dry-run default) |
| Component probes (forms, editors, iframes, scroll, upload) | ✅ |

**MCP tools:** `perception_plan_component_search`, `perception_search_components`, `perception_select_component_foundation`, `perception_integrate_component`, `perception_probe_form`

See [features/component_intelligence_architecture.md](./features/component_intelligence_architecture.md) (complete pipeline) and [features/component_intelligence.md](./features/component_intelligence.md) (Phase 1 search).

---

## 3. Design Workflow Intelligence

**Path:** `design_workflow_intelligence/`

Integrates design tools and multi-step workflows.

| Capability | Status |
|------------|--------|
| Flow graphs + runners | ✅ |
| State save/restore | ✅ |
| Auth gates + route guards | ✅ |
| Exploration + feature flags | ✅ |
| Navigation hints (codebase → browser) | ✅ |
| Figma / Penpot / Framer / Excalidraw | 📋 planned |
| Design-to-code, tokens, assets | 📋 planned |

**MCP tools:** `perception_flow_describe`, `perception_state_*`, `perception_auth_gate`, `perception_probe_guards`

---

## 4. Visual & Browser Intelligence

**Path:** `visual_browser_intelligence/`

Interacts with the running application.

| Subpackage | Contents |
|------------|----------|
| `observe/` | scan, observation, preflight |
| `verify/` | SuccessCriteria, verify, JS evaluation |
| `actions/` | scripted_actions |
| `visual/` | screenshots, visual_diff, MCP image responses |
| `live/` | websocket_observer |
| `browser/` | SessionStore, session lifecycle |
| `agent/` | optional Browser Use LLM path |

**MCP tools:** `perception_session_*`, `perception_navigate*`, `perception_observe`, `perception_execute_*`, `perception_verify`

---

## 5. Design Snapshot Engine

**Path:** `design_snapshot_engine/`

Converts live browser state into a **unified `DesignSnapshot`** — the common language for all design-related intelligence modules. Observes, extracts, normalizes, and measures. **Never critiques.**

| Extractor | Report section |
|-----------|----------------|
| Typography, Spacing, Color, Layout, Grid | `typography`, `spacing`, `colors`, `layout`, `grid` |
| Hierarchy, Components, Motion, Accessibility, Design tokens | `hierarchy`, `components`, `motion`, `accessibility`, `design_tokens` |

**API:** `DesignSnapshotService.capture(session, observation=...)`

Optional **designlang** augment when `DESIGNLANG_ENABLED=1` (see `integrations/designlang.py`).

See `design_snapshot_engine/ARCHITECTURE.md`.

---

## 6. Design Reference Registry

**Path:** `design_reference_registry/`

Stores **Design Snapshots** (not screenshots) for reference products. Supports structural similarity search and snapshot-to-snapshot comparison.

**API:** `DesignReferenceRegistry.register()`, `find_similar()`, `compare()`

---

## 7. Codebase Intelligence

**Path:** `codebase_intelligence/`

Understands the frontend codebase via Code Review Graph (CRG).

| Capability | Status |
|------------|--------|
| Project / component / route graph | ✅ (CRG) |
| Semantic search | ✅ |
| `ICodeGraph` provider abstraction | ✅ |

**MCP tools:** `perception_code_context`

---

## 8. Frontend Quality Intelligence

**Path:** `frontend_quality_intelligence/`

Validates production readiness and debugging signals.

| Subpackage | Contents |
|------------|----------|
| `console/` | CDP console ring buffer |
| `network/` | CDP network + HAR |
| `audits/` | Lighthouse wrappers |
| `reports/` | diagnosis orchestration |
| `dev_insights.py` | Observe-window quality bridge |
| `diff.py` | Scan regression diff |

**MCP tools:** `perception_console_*`, `perception_network_*`, `perception_audit_*`, `perception_full_diagnosis`, `perception_debug_mode`, `perception_audit_mode`, `perception_diff`

---

## 9. Design Sense Intelligence

**Path:** `design_sense_intelligence/`

UI/UX **review and critique orchestration** — reasons over `DesignSnapshot` reports (layout, hierarchy, usability, craft). Does **not** extract DOM/CSS or enforce design-system math (see module 10).

| Capability | Status |
|------------|--------|
| Visual layout heuristics (`visual_insights`) | ✅ |
| Quality report hints (`quality_hints`) | ✅ |
| Specialist reviewers + Review Coordinator | 🚧 scaffold |
| Provider adapters (Open Design, Design Lint, Microsoft, UICrit, Crit/Rams) | 🚧 scaffold |
| Design Lint rule engine port (DOM/CSS) | 🚧 scaffold |
| Full design review MCP tool | 📋 planned |

See [features/design_sense_intelligence.md](./features/design_sense_intelligence.md).

Consumed during observe (`visual_insights`) and diagnosis (`quality_hints`). Component Intelligence consumes `contract.py`.

---

## 10. Consistency Intelligence

**Path:** `consistency_intelligence/`

Ensures the frontend remains **mathematically and visually consistent** with the design system. Detects drift, scores inconsistencies, and (future) suggests or applies fixes. **Not** UX coaching — that is Design Sense Intelligence.

| Capability | Status |
|------------|--------|
| Module scaffold (`service`, `models`, `rules/`) | ✅ |
| Design token extraction | 📋 planned |
| Spacing / typography / color scale validation | 📋 planned |
| Border radius, shadows, layout grid rules | 📋 planned |
| Component + interaction-state consistency | 📋 planned |
| Visual hierarchy + responsive consistency | 📋 planned |
| Consistency scoring + fix suggestions | 📋 planned |

**MCP tools (planned):** `perception_consistency_audit`, `perception_consistency_diff`, `perception_token_snapshot`

See [features/consistency_intelligence.md](./features/consistency_intelligence.md).

---

## 11. Inspiration Intelligence

**Path:** `inspiration_intelligence/`

Orchestrates **public design inspiration** from curated gallery sites. Generalized from the former Figma Community inspiration pipeline. Browser automation is execution-only; ranking and evaluation stay in intelligence modules.

| Capability | Status |
|------------|--------|
| Intent parsing + search planning | ✅ |
| **Community Intelligence** (query expansion — not Figma-specific) | ✅ |
| Priority provider cascade + early stop | ✅ |
| Dribbble provider adapter | ✅ |
| Behance / One Page Love / Awwwards / SiteInspire / Godly / Land-book | ✅ gallery adapters |
| Candidate Intelligence + ranking + selection | ✅ |
| Ephemeral vision blobs (session-scoped) | ✅ |
| Capture → Design Snapshot bridge | 📋 scaffold |
| MCP tools: `perception_inspiration_discover`, `perception_inspiration_collect`, `perception_inspiration_session_end` | ✅ |
| Provider navigation documentation | ✅ |

**Provider priority:** Dribbble → Behance → One Page Love → Awwwards → SiteInspire → Godly → Land-book (stop when enough high-confidence hits).

See `inspiration_intelligence/docs/ARCHITECTURE.md`, `inspiration_intelligence/docs/INSPIRATION_AGENT_GUIDE.md`, and `inspiration_intelligence/docs/providers/`.

---

## 12. Figma Intelligence

**Path:** `figma_intelligence/`

**Connection + coordination layer** for the user's Figma workspace via **southleft/figma-console-mcp**. Returns normalized `FigmaDesignContext` — not design critique or public inspiration.

| Capability | Status |
|------------|--------|
| Connection Manager (PAT connect, validate, store) | ✅ |
| Session Manager (file, page, frame, selection) | ✅ |
| Figma Console MCP Adapter | ✅ |
| Context Normalizer + Design Cache + Coordination | ✅ |
| Health Monitor | ✅ |
| MCP: `perception_figma_connect`, `_status`, `_context` | ✅ |
| Legacy community pipeline (discover / extraction) | ✅ retained |

See [features/figma_intelligence.md](./features/figma_intelligence.md) and `perception://figma-guide`.

**Boundary:** Inspiration Intelligence → public galleries. Design Sense → critique. Component Intelligence → components. Figma Intelligence → user's Figma connection + normalized context only.

---

## 13. Resource Intelligence

**Path:** `resource_intelligence/`

Orchestrates **production-ready creative assets** — icons, illustrations, photos, fonts, logos, avatars, 3D, patterns, animations, mockups. License-aware; not a CDN or asset host.

| Capability | Status |
|------------|--------|
| Provider comparison matrix (40+ ecosystems) | ✅ research |
| Resource Graph schema | ✅ |
| License Intelligence architecture | ✅ |
| Ranking + Planning architecture | ✅ |
| MCP tool specification | ✅ |
| Provider adapters (Iconify, Pexels, Fontsource, …) | 📋 Phase 2 |
| `perception_resource_search` + category tools | 📋 Phase 5 |

**Excluded automation:** unDraw (AI/scrape ban), Storyset (robot/scraper ban).

See `resource_intelligence/docs/ARCHITECTURE.md` and [features/resource_intelligence.md](./features/resource_intelligence.md).

**Boundary:** Component Intelligence owns installable UI components; Resource Intelligence owns discrete assets (SVG, font files, stock photos).

---

## 14. SEO Intelligence

**Path:** `seo_intelligence/`

Orchestrates **free-first SEO evidence** — Search Console, GA4, LibreCrawl, Lighthouse, Browser Intelligence. Not Ahrefs, Semrush, or an internet-scale crawler.

| Capability | Status |
|------------|--------|
| Architecture + provider matrix | ✅ |
| SEO Knowledge Graph schema | ✅ |
| Live provider adapters (GSC, GA4, LibreCrawl, Lighthouse, Browser) | ✅ |
| Cross-analysis + recommendations + verification loop | ✅ |
| Capability-aware planner + fallbacks | ✅ |
| AI-native recommendation pipeline + reasoning_context | ✅ |
| `perception_seo_status` + `perception_seo_audit` + `perception_seo_connect` + `perception_seo_verify` | ✅ |

**Do not build:** keyword databases, backlink crawlers, SERP databases.

See `seo_intelligence/docs/ARCHITECTURE.md` and [features/seo_intelligence.md](./features/seo_intelligence.md).

**Boundary:** SEO Intelligence owns search performance orchestration. Browser Intelligence owns live observation (consumed via adapter). `perception_audit_seo` (Frontend Quality) remains a page-level Lighthouse audit — SEO Intelligence correlates multi-source evidence.

---

## Core package

**Path:** `core/`

Shared across modules — no domain intelligence.

| Module | Role |
|--------|------|
| `envelope.py` | MCP contract v1.0 responses |
| `scan_registry.py` | `scan_id` artifact hub |
| `cdp_hub.py` | CDP event multiplexing |
| `artifacts.py` | Artifact path helpers |
| `budget.py` | Output truncation |

---

## Adding a new capability

1. Identify the owning intelligence module.
2. Add logic under that module's `service.py` or subpackage.
3. If external: add a `providers/` implementation + `registry.py` entry.
4. Wire a thin handler in `mcp/handlers.py` and schema in `mcp/tools.py`.
5. Document in `docs/features/<module>.md` and `docs/tool_reference.md`.
6. Add contract test in `src/run_mcp_contract_tests.py`.

Do **not** add domain logic to `mcp/` or `core/`.

---

## Related

- [architecture.md](./architecture.md) — system overview
- [roadmap.md](./roadmap.md) — version milestones
- [design_decisions.md](./design_decisions.md) — ADRs
