# Design decisions

ADR-style log. New entries at top.

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
