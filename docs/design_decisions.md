# Design decisions

ADR-style log. New entries at top.

---

---

## ADR-018 — Stable intelligence contracts for Component Intelligence (2026-07-10)

**Context:** Component Intelligence orchestration was blocked waiting for Design Sense, Consistency, and browser validation to mature. Direct imports of `component_guidance.py` would force orchestration changes as each module evolves.

**Decision:** Define versioned contracts (`component_intelligence/contracts/`, `CONTRACT_VERSION=1.0`) for Framework, Codebase, Design Sense, Consistency, and Browser intelligence. Each peer module ships `contract.py` implementing the protocol; heuristic/placeholder logic stays behind the API. Component Intelligence calls contracts only — orchestration, MCP tools, and pipeline stages do not change when implementations deepen. `IntegrationRequest.execute_install` and `execute_repairs` default to false (plan-only).

**Consequences:** Modules evolve independently. Today’s adapters return heuristics with `degraded[]`; future work replaces adapter internals (Grounded Docs, token validators, observe/verify) without touching `orchestrator.py`. New intelligence modules add a contract + adapter and register in `IntelligenceContracts`.

---

## ADR-017 — Component Intelligence orchestration refactor (2026-07-10)

**Context:** Fixed percentage weights (30/25/25/20) and a monolithic IntegrationEngine do not match how modern coding agents combine expert module outputs.

**Decision:** (1) Remove composite scoring — each module returns structured guidance; `guidance/synthesis.py` merges with priority rules. (2) Split integration into single-responsibility modules: Documentation Reader → Installation Planner → Dependency Resolver → Compatibility Resolver → Installer → Component Adapter, orchestrated by `IntegrationPipeline`. (3) Repair loop consults Framework, Codebase, and Documentation Reader via `fix_planner.py` before generating `FixPlan`.

**Consequences:** `DocumentationBundle`, `InstallationPlan`, `InstallResult` replace flatter artifacts. Implementation phases remain scaffolded with `degraded[]` until each subsystem is wired.

---

## ADR-016 — Component Intelligence orchestrator (2026-07-10)

**Context:** Phase 1 search finds components but agents fail at install, adaptation, and validation. Component Intelligence must coordinate all intelligence modules, not search in isolation.

**Decision:** Extend `component_intelligence/` with `selection/`, `integration/`, `validation/`, `orchestrator.py`, and cross-module `component_guidance.py` entrypoints on Framework, Codebase, Design Sense, and Consistency modules. Pipeline: search → filter → parallel guidance → foundation selection → integration engine (docs, deps, compatibility, adapter, install) → browser validation → repair loop. MCP tools: `perception_select_component_foundation`, `perception_integrate_component`. Consistency guidance **never hard-rejects** — only modification lists.

**Consequences:** Phases 2–5 scaffolded with `degraded[]` until install, browser wiring, and token validators land. Ranking weights and repair actions evolve without MCP contract breaks.

---

## ADR-011 — Dedicated Lighthouse Chrome for audits (2026-07-09)

**Context:** Attaching Lighthouse to the managed Browser Use CDP port disrupts the session (WebSocket reconnects, hub conflicts).

**Decision:** Run Lighthouse CLI with `--preset=desktop` in a dedicated headless Chrome against the **same URL** the session is viewing. Treat valid output JSON as success even when Windows cleanup returns EPERM.

**Consequences:** Audit browser state may differ slightly from managed session (cookies/auth); document that agents should navigate first, then audit. No disruption to console/network collectors.

---

## ADR-010 — Network module with prioritized reports (2026-07-09)

**Context:** v0.5 needs full network capture; observe windows can include hundreds of asset requests.

**Decision:** `navigation/network/` with session ring buffer; reports prioritize failures/API/slow before asset noise; failures counted across full window not just `limit` slice; HAR written to `artifacts/.../network/` even without screenshots.

**Consequences:** `agent_summary.network` includes `failed_count`, `har_path`; `dev_insights` network signals remain for backward compatibility.

---

## ADR-009 — Console module via shared CDP hub (2026-07-09)

**Context:** v0.4 needs full console history without duplicating BrowserTools extension architecture.

**Decision:** `navigation/console/` with `SessionConsoleService` attached at session start; `ConsoleCollector` fans in via existing `DevInsightsHub`. Observe windows marked before navigation in `scan_page`.

**Consequences:** `dev_insights` remains for blocking network/UI signals; `agent_summary.console` is the structured console section. Two collectors on one hub — tested fan-out.

---

## ADR-008 — Reference clone, not dependency (2026-07-09)

**Context:** BrowserTools MCP has useful features (audits, console/network) but inactive architecture (extension + middleware).

**Decision:** Clone to `references/browser-tools-mcp/` for study only. Reimplement via CDP in our modules.

**Consequences:** No npm dependency on `@agentdeskai/*`. Slower initial audit port; full control over schema and security.

---

## ADR-007 — Inline images in MCP tool results (2026-07-09)

**Context:** Agents miss screenshots when only `scan_id` + resource URI returned.

**Decision:** Return `ImageContent` in tool `content[]` alongside JSON text; keep resources for deep links.

**Consequences:** Larger payloads; requires Pillow; better agent UX vs BrowserTools screenshot-only tools.

---

## ADR-006 — Deterministic server, agent is brain (2026-07-08)

**Context:** Browser Use can run full LLM agents; BrowserTools returns raw logs.

**Decision:** MCP never calls LLM for reasoning. `agent_summary` is structured facts + playbook hints as data, not generated prose.

**Consequences:** Host agent must follow AGENT_GUIDE; server stays testable and cheap.

---

## ADR-005 — Managed Chromium default (2026-07-08)

**Context:** Extension attach vs CDP-managed browser.

**Decision:** Default to Browser Use managed session. Optional attach mode deferred to v0.8.

**Consequences:** No extension install; reproducible CI; attach mode needs separate security doc.

---

## ADR-015 — Consistency Intelligence vs Design Sense (2026-07-10)

**Context:** Agents need both UX reasoning ("is this a good pattern?") and design-system enforcement ("does this match our tokens and scales?"). Combining both in one module would blur responsibilities and make rules harder to test.

**Decision:** Add `consistency_intelligence/` as the **8th intelligence module**, separate from `design_sense_intelligence/`. Consistency Intelligence owns mathematical/visual consistency: design tokens, spacing systems, typography scales, color usage, radii, shadows, grids, component parity, interaction states, hierarchy, and responsive consistency. It detects inconsistencies, scores them, and will eventually suggest or apply fixes. Design Sense remains qualitative UX heuristics only. Scaffold only in v1.3 — no MCP tools until validators exist.

**Consequences:** Future consistency tools consume observations from Visual Browser Intelligence and paths from Codebase Intelligence; they do not duplicate Lighthouse or `visual_insights`. Planned tools: `perception_consistency_audit`, `perception_consistency_diff`, `perception_token_snapshot`.

---

## ADR-014 — Seven intelligence modules + core (2026-07-09)

**Context:** The MCP grew as flat packages (`perception/`, `console/`, `codeGraph/`) making it hard to extend one domain without touching unrelated code.

**Decision:** Restructure `src/navigation/` into seven intelligence modules (framework, component, design workflow, visual/browser, codebase, frontend quality, design sense) plus shared `core/`. Each module owns providers, registry, service, models, and cache where applicable. Legacy import paths remain as shims.

**Consequences:** New capabilities extend a single module; MCP handlers stay thin. Physical file moves completed in v1.1; shims can be removed in a future major version.

---

## ADR-013 — Framework Intelligence provider abstraction (2026-07-09)

**Context:** Agents need version-specific framework docs during UI work, but the MCP must not embed or maintain framework knowledge.

**Decision:** `framework_intelligence/` detects stack locally, routes documentation requests via `DocumentationProvider`, normalizes to `FrameworkKnowledgeResponse`, and caches by `framework:version:topic`. Grounded Docs MCP is the first provider; all custom logic lives in `providers/grounded_docs/` so upstream can be merged easily. Handlers never expose provider-specific response shapes.

**Consequences:** Node.js 22+ required for live doc fetch; without CLI/network the detector still works via `perception_detect_framework`. Future providers plug in without MCP contract changes.

---

## ADR-012 — Diagnosis orchestrator, no LLM in server (2026-07-09)

**Context:** Agents need one-shot QA reports combining observe, console, network, and Lighthouse without raw log dumps.

**Decision:** `navigation/reports/` orchestrates subsystems into `PerceptionReport`. Suggested fixes are rule-based hints only; no LLM text generation in MCP server. Three modes: `debug` (no audits), `full` (a11y + performance), `audit` (all four Lighthouse categories).

**Consequences:** `perception_full_diagnosis` may take minutes with audits; `run_audits=false` and `perception_debug_mode` provide fast paths. Reports persist as `diagnosis.json` / `diagnosis.md` scan resources.

---

## ADR-004 — Scan store as artifact hub (2026-07-08)

**Context:** Where to put screenshots, reports, HAR files.

**Decision:** Every observe/verify creates `scan_id` under session scan store; resources addressable by URI.

**Consequences:** Enables diff, regression, future HAR/console attachments per scan.

---

## ADR-003 — dev_insights as bridge to console/network modules (2026-07-08)

**Context:** Need errors/network signals before full CDP modules exist.

**Decision:** `dev_insights.py` collects console + network failures during observe window; later modules feed same `agent_summary` schema.

**Consequences:** Avoid breaking MCP contract when v0.4/v0.5 land; may duplicate until refactor.

---

## ADR-002 — Contract tests over stdio E2E (2026-07-08)

**Context:** Full Cursor MCP stdio tests are heavy.

**Decision:** `run_mcp_contract_tests.py` calls handlers directly with live sandbox dev server.

**Consequences:** Fast CI; gap for MCP wire protocol regressions (backlog).

---

## ADR-001 — PyPI dual package (2026-07-09)

**Context:** Name confusion `frontend-perception-engine` vs `frontend-mcp`.

**Decision:** Primary library + thin alias package with same entry points.

**Consequences:** Two publishes per release; README documents both.
