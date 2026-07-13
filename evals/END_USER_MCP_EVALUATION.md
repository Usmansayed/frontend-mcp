# End-User MCP Evaluation — `frontend-mcp` v1.0.1

**Date:** 2026-07-13  
**Method:** Hands-on evaluation via Cursor MCP server `user-frontend-mcp` (installed PyPI package `frontend-mcp==1.0.1`). No local `src/`, contract runners, or dev scripts.  
**Target app:** `http://localhost:5173` (Navigation Maze sandbox)  
**Evaluator:** AI agent using `CallMcpTool` only  

> **Retest (2026-07-13 10:37 AM):** Full E2E re-run on `user-frontend-mcp` v1.0.1 with sandbox started. Session `sess_6bb04e68568d`, episode `ep_a098fcea33f6473989ab1b47399352b7`, scan `scan_e93607fba182`. All core browser + design + component integrate tools passed when run **one at a time**. `perception_health` correctly reported unreachable (attempt 3, `TR_DEV_SERVER_DOWN`) before sandbox was started, then `ok:true` after. `perception_integrate_component` returned in 6ms (degraded, no repo) — previous hangs were caused by parallel tool batches, not this tool alone. MCP resources still not fetchable in Cursor.

---

## Executive summary

**Verdict: Production-usable for core browser + design + component + icon resource workflows; not yet reliable for full SEO audit or some resource providers.**

v1.0.1 fixed the v1.0.0 packaging blocker (`coordination_layer/runtime/manifest.json`). During testing, **22 distinct tools** returned valid v1.0 envelopes. One heavy tool (`perception_seo_audit`) timed out at 90s. Two tools (`perception_code_context`, `perception_integrate_component`) hung the MCP when invoked after a long browser session. MCP resources (`perception://agent-guide`) were not readable through Cursor’s resource fetch API.

| Area | Tested | Passed | Partial | Failed |
|------|--------|--------|---------|--------|
| Core browser | 8 | 7 | 0 | 1 (hang risk on code_context) |
| Design | 2 | 2 | 0 | 0 |
| Components | 3 | 2 | 0 | 1 (integrate hung) |
| Resources | 4 | 2 | 2 | 0 |
| SEO | 2 | 1 | 0 | 1 (audit timeout) |
| AI Visibility | 1 | 0 | 1 | 0 (status only; audit timeout) |
| Coordination | 3 | 3 | 0 | 0 |
| Execution runtime | all calls | ✓ | — | — |
| Cross-module E2E | 1 | 1 | 0 | 0 |
| MCP resources | 2 | 0 | 0 | 2 |

**Overall platform score (installed MCP): 7.2 / 10**

---

## 1. Overall assessment

The installed MCP delivers on its core promise: a **deterministic browser runtime** with structured v1.0 envelopes, screenshots, form probing, verification, and rich specialist modules (design, components, resources, inspiration, coordination). An end user (or host agent like Cursor/Claude) can run a full **observe → probe → verify → design review** loop on a live dev server without writing custom automation.

Strengths are unusually deep for an MCP: live form validation discovery, route-guard probing, design snapshots with multi-reviewer consensus, shadcn component search, Lucide icons with verified npm imports, and an invisible coordination layer that tracks episode state and suggests next capabilities.

Weaknesses observed in real use: **SEO audit timeout**, **font/pattern resource gaps**, **MCP resources not exposed to Cursor**, **occasional MCP hangs** after extended sessions, **large observe payloads** (~1 MB JSON + images), and **parameter naming friction** (`website_url` not `url` for SEO audit). Coordinator cluster inference can jump aggressively (e.g. component search while doing browser work) though per-tool coordinator blocks are generally helpful.

---

## 2. Feature-by-feature review

### 2.1 Core browser workflows — **Strong (8.5/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_health` | ✅ | `ok:true`, HTTP 200, `latency_ms:226`, idempotency replay on repeat |
| `perception_session_start` | ✅ | Session `sess_9ef79a00a9ad`, browser launch ~3s, artifacts dir created |
| `perception_navigate_and_observe` | ✅ | `scan_2328b2b563b2`, annotated screenshot, DOM insights, network/console |
| `perception_probe_form` | ✅ | 4 live rules (email, phone, age, terms); `invalid_verified` + `valid_verified` |
| `perception_verify` | ✅ | `verified:true` for `text_contains: ["Forms Playground"]`, ~123ms |
| `perception_probe_guards` | ✅ | `/dashboard` → redirect to `/login`; admin route needs role |
| `perception_auth_gate` | ✅ | `requires_human:false` on public form page |
| `perception_flow_describe` | ✅ | `validation-form`, `shop-order` flows listed |
| `perception_code_context` | ❌ hang | Call did not return (session blocked ~7+ min) |

**What worked well**
- Full AGENT_GUIDE loop executable: health → session → observe → probe → verify.
- Form probe discovers real validation messages from live submit (not static docs).
- Verify is fast (~100–160ms) after observe.
- Screenshots returned inline (annotated + raw) — primary evidence for agents.
- `agent_summary.blocking` vs `advisory` separation is clear; blocking was empty on tested pages.

**Bugs / friction**
- `perception_code_context` without `repo_root` appears to hang (likely CRG graph init on cwd).
- Observe responses are very large (~1 MB) — context-heavy for LLM hosts.
- Parallel tool calls after a browser session caused multi-minute hangs in one test batch.

**Performance**
- Health: &lt;400ms
- Session start: 2–10s (browser cold start)
- Observe: several seconds (network capture + screenshot)
- Verify: ~100–160ms

---

### 2.2 Design workflows — **Strong (8/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_build_design_snapshot` | ✅ | `snap_02f4a42abfe4`, 7 palette colors, 22 interactives, 0 WCAG failures |
| `perception_design_review` | ✅ | `passed:true`, 7 minor findings (color tokens, typography scale), 9 reviewers |

**Strengths**
- Snapshot extracts typography, spacing, contrast matrix, layout tree from live page.
- Design review runs multi-reviewer consensus (layout, typography, color, a11y, UX, motion).
- Findings are structured: severity, evidence, recommendation, confidence.
- `passed:true` with only minor issues — sensible for sandbox form page.

**Weaknesses (observed)**
- `degraded` list long: `design_lint_error:IndexError`, `open_design_not_configured`, heuristic-only providers.
- Several external design providers are methodology markers, not live integrations.
- Review latency was very fast (9–12ms) — suggests snapshot-local analysis, not deep external calls.

---

### 2.3 Component workflows — **Good (7.5/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_search_components` | ✅ | "date picker" → `shadcn:date-picker-demo` + ranked candidates |
| `perception_plan_component_search` | ✅ | Parsed `calendar` + `form` intents, 5 planned queries, registry list |
| `perception_integrate_component` | ❌ hang | Did not return in test |

**Strengths**
- Search returns install commands, registry metadata, relevance scores.
- Plan tool gives host agent a refinement step before search (good UX for LLMs).
- Coordinator correctly switched to `search_select_integrate.component` playbook after component tools.

**Weaknesses**
- `perception_integrate_component` hung — integration guidance not verified end-to-end.
- Without `repo_root`, intelligence context is empty (`framework: ""`).

---

### 2.4 Resource workflows — **Mixed (6/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_resource_icon_search` | ✅ | 12 Lucide icons, `verified_import`, `npm install lucide-react` |
| `perception_resource_search` | ✅ | Same quality for `check` query |
| `perception_resource_pattern_search` | ⚠️ empty | `provider_not_implemented:hero-patterns`, `blocking: no_resource_assets` |
| `perception_resource_font_search` | ⚠️ empty | `fontsource_search_failed:HTTP Error 400` for query `inter` |

**Strengths**
- Icon search is excellent for agents: MIT license, import line, usage snippet, no blobs needed.
- `agent_summary.selection` picks a primary asset with alternatives.
- License warnings surfaced (`ai_training_prohibited`).

**Weaknesses**
- Pattern and font providers failed in real calls (not just “no results”).
- `repo_root` empty → `hints_without_repo_root` in inspiration/resource cross-calls.

---

### 2.5 SEO workflows — **Partial (5/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_seo_status` | ✅ | Full status: modes, providers, LibreCrawl companion, OAuth state |
| `perception_seo_audit` | ❌ timeout | `ok:false`, `timed out after 90.0s`, `failure_class:timeout` |

**Parameter trap (observed)**
- `perception_seo_audit` with `url` → **Input validation error: `'website_url' is a required property`**
- Correct param is `website_url` (documented in tool schema but easy to miss)

**Strengths**
- Status tool is fast (~100–170ms) and self-describing (development vs professional modes).
- AI visibility advertised: 12 analyzers in status block.
- LibreCrawl + Lighthouse marked available; companion auto-start documented.

**Weaknesses**
- Full audit did not complete in 90s (LibreCrawl/Lighthouse bootstrap suspected).
- After timeout, coordinator returned `stop_reason: anti_pattern_block` — confusing post-failure state.
- No successful `perception_seo_query` or `perception_seo_verify` in this session.

---

### 2.6 AI Visibility workflows — **Status only (4/10)**

AI visibility was **not exercised end-to-end**. `perception_seo_status` reports:

```json
"ai_visibility": {
  "phase": "ai_readiness_v1",
  "analyzers": 12
}
```

`perception_seo_audit` with `include_ai_visibility: true` was attempted but **timed out** before returning analyzer results. Cannot score analyzer quality without a completed audit envelope.

---

### 2.7 Coordination layer — **Good with caveats (7.5/10)**

| Tool | Result | Evidence |
|------|--------|----------|
| `perception_coordinator_briefing` | ✅ | Full PSM JSON, capability posture, evidence domains |
| Coordinator on each tool | ✅ | `coordinator.integrated: true` on all tested tools |
| Episode binding | ✅ | `ep_5fd1e1ab90964165bb0e0e51b2ed2234` bound to session |

**What worked well**
- After `session_start`, coordinator suggests `browser_observe` — correct bootstrap.
- After `probe_form`, suggests `invalid_before_valid.form` with compiled `perception_verify` step — **excellent** for host agents.
- After `verify`, PSM shows `verification_status: passed`, `ui_runtime.posture: verified`.
- `completed_step_ids` tracks observe → probe → invalid_path → snapshot → review accurately in fresh episode.

**Incorrect / surprising coordinator behavior (observed)**
- Calling `perception_search_components` while in browser workflow jumped cluster to `cluster.component.acquisition_pipeline` at `S07_verification` — aggressive context switch.
- After SEO audit timeout: `stop_reason: anti_pattern_block`, `suggested_capability: null` — dead end without recovery hint.
- After design review without `repo_root`: `stop_reason: missing_artifact:repo_root` — correct diagnosis but no default path for installed-only users.
- Earlier mixed episode (`ep_f053d723...`) showed **stale PSM** in briefing vs per-tool coordinator blocks; fresh session fixed this.

---

### 2.8 Execution runtime — **Excellent (9/10)**

Observed on every successful tool call:

```json
"execution": {
  "execution_id": "ex_...",
  "correlation_id": "corr_2f369e4d7dfe4703",
  "tool": "perception_health",
  "attempt": 1,
  "latency_ms": 393,
  "failure_class": "none",
  "recovery_trigger": null,
  "replayed": false,
  "idempotency_key": "perception_health:908e3162bd6912f7da49b81d"
}
```

**Observations**
- Shared `correlation_id` across a session — good for tracing.
- `perception_health` repeat returned `replayed: true`, `latency_ms: 0` — idempotency works.
- `perception_probe_form` showed `attempt: 3` in earlier session — retry policy engaged, then succeeded.
- SEO audit timeout: `failure_class: timeout`, `recovery_trigger: TR_VERIFY_FAIL`, `latency_ms: 90015` — failure taxonomy is useful.

---

### 2.9 Cross-module workflows — **Good (8/10)**

**E2E path executed (single session):**

```
health → session_start → navigate_and_observe(/forms/validation)
  → probe_form → verify → build_design_snapshot → design_review
  → coordinator_briefing → auth_gate
```

Parallel module calls (resource search during browser session) also worked but perturbed coordinator cluster.

**Strengths**
- Modules compose naturally via `scan_id` / `session_id`.
- Design pipeline consumes browser scan without re-navigation.
- Coordinator tracks cross-module evidence (`ui_runtime`, `design_source`, `design_system` postures).

**Friction**
- No single “workflow” tool — host agent must orchestrate (by design, but higher skill floor).
- Missing `repo_root` blocks design PDG refresh and codebase-aware component/resource hints.

---

### 2.10 End-to-end engineering tasks — **Partial (7/10)**

| Task | Outcome |
|------|---------|
| Validate form rules on live page | ✅ Complete via probe_form |
| Confirm page renders | ✅ observe + verify |
| Pick icon for UI | ✅ resource search with import |
| Find shadcn date picker | ✅ component search |
| Design quality check | ✅ snapshot + review |
| SEO audit dev site | ❌ Timeout |
| Connect Figma | ⚠️ Status only — Desktop Bridge not open (clear instructions returned) |
| Inspiration mood board | ✅ Dribbble discovery (WAF degraded) |
| Full validation-form flow (invalid submit → valid fill) | ⚠️ Not completed — probe done, act/fill not run |

---

### 2.11 MCP resources — **Failed in Cursor (2/10)**

| Resource | Result |
|----------|--------|
| `perception://agent-guide` | `MCP resource not found` (Cursor FetchMcpResource) |
| `perception://seo-guide` | `MCP resource not found` |

Tools reference these resources in `agent_summary.advisory` but the host could not read them through Cursor’s resource API during testing. This is a significant onboarding gap for agents instructed to “read agent-guide at session start.”

---

## 3. Strengths by module

| Module | Top strengths |
|--------|----------------|
| **Browser** | Live observe + screenshots + verify loop; form probe with real validation rules |
| **Design** | Snapshot + multi-reviewer consensus; structured findings with severity |
| **Components** | shadcn ecosystem search + search plan with query expansion |
| **Resources (icons)** | Verified imports, license blocks, npm install commands |
| **SEO (status)** | Clear mode matrix, companion services, OAuth readiness flags |
| **Inspiration** | Multi-provider discovery plan; Dribbble candidates with profiles |
| **Figma** | Honest disconnected state + step-by-step Desktop Bridge recovery |
| **Coordination** | Per-tool briefing with compiled verify steps; PSM evidence lattice |
| **Execution runtime** | Correlation IDs, idempotency, retry attempts, failure_class |

---

## 4. Weaknesses (evidence-based only)

1. **SEO audit timeout** — 90s hard fail; no partial results returned.
2. **MCP resources unreachable in Cursor** — guides referenced but not fetchable.
3. **MCP hangs** — `code_context` and `integrate_component` blocked server; parallel calls worsened it.
4. **Resource provider gaps** — hero patterns not implemented; fontsource 400 errors.
5. **Large observe payloads** — costly for token-limited agents.
6. **Parameter naming** — `website_url` vs `url` on SEO audit.
7. **No `repo_root` defaults** — installed-only users lack codebase/PDG integration unless they set env.
8. **Coordinator cluster jumping** — unrelated tool calls can flip playbook context.
9. **Unknown tool errors** — Cursor rejects invalid tool names client-side (never reaches MCP envelope).
10. **v1.0.0 → v1.0.1** — earlier install was completely broken; users on 1.0.0 need upgrade.

---

## 5. Improvement recommendations

### P0 — Reliability
1. **SEO audit**: return partial progress on timeout; stream evidence as collected; document minimum companion requirements.
2. **Hang prevention**: hard timeout + envelope for `code_context` when graph unavailable; never block stdio >30s.
3. **MCP resources**: fix Cursor resource registration or ship guides via `perception_*` read tool fallback.
4. **Post-timeout coordinator**: replace `anti_pattern_block` with actionable recovery (retry, skip LibreCrawl, browser-only audit).

### P1 — Agent UX
5. **Smaller observe mode**: `summary_only` default for repeat observes; full DOM on demand.
6. **Install wizard output**: `frontend-mcp-install` should set `FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT` in Cursor config.
7. **Alias params**: accept `url` as alias for `website_url` on SEO tools.
8. **Resource providers**: implement hero-patterns or remove tool until ready; fix fontsource query.

### P2 — Polish
9. **Coordinator stability**: don’t advance to `S07_verification` on read-only module calls (component search).
10. **Session cleanup**: `perception_session_end` prompt in server instructions after long runs.
11. **Published smoke test**: PyPI install + health + observe + verify in CI (stdio MCP).

---

## 6. Architecture observations

```
Host LLM (Cursor / Claude)
    ↓ MCP stdio — CallMcpTool
frontend-mcp v1.0.1 (PyPI)
    ↓
ExecutionRuntime (retry, idempotency, correlation, timeout)
    ↓
Handler (browser / design / seo / …)
    ↓
CoordinatorBridge (PSM update, briefing, capability routing)
    ↓
Envelope v1.0 + optional images
```

- **Host LLM is the brain** — server returns facts; `agent_summary.advisory` never says “you should next” as imperative planning hints in tool bodies (coordinator `compiled_step` is structural, not prose).
- **Coordination is additive** — every tool can include `coordinator` block without breaking `ok`.
- **Bundled artifacts** (v1.0.1) — coordination R0–R11 under `navigation/coordination_intelligence/artifacts/runtime/`.
- **Companion processes** — SEO pulls LibreCrawl native process; failure modes affect audit latency.

---

## 7. Production readiness

| Gate | Status |
|------|--------|
| Install via pip/uvx | ✅ v1.0.1 |
| First tool call works | ✅ (v1.0.0 was ❌) |
| Browser loop | ✅ |
| Design loop | ✅ |
| Component search | ✅ |
| Icon resources | ✅ |
| SEO full audit | ❌ timeout in test env |
| MCP resources in Cursor | ❌ |
| Long-session stability | ⚠️ hangs observed |
| Documented prerequisites | ⚠️ sandbox + optional companions |

**Production readiness: Conditional pass** — ship for browser/design/component/icon use cases; document SEO companion setup and recommend `repo_root` for full platform.

---

## 8. Module scorecard

| Module | Score | Confidence |
|--------|-------|------------|
| Core browser | **8.5 / 10** | High — many tools tested |
| Design intelligence | **8.0 / 10** | High |
| Component intelligence | **7.5 / 10** | Medium — integrate not completed |
| Resource intelligence | **6.0 / 10** | High — icons great, fonts/patterns failed |
| SEO intelligence | **5.0 / 10** | Medium — status ok, audit failed |
| AI Visibility | **4.0 / 10** | Low — status only |
| Inspiration intelligence | **7.0 / 10** | Medium — discover ok, WAF degraded |
| Figma intelligence | **6.5 / 10** | Medium — status only, clear offline path |
| Coordination layer | **7.5 / 10** | High |
| Execution runtime | **9.0 / 10** | High |
| MCP resources / guides | **2.0 / 10** | High — failed fetch |
| Reliability / ops | **6.0 / 10** | Medium — hangs + timeout |

---

## 9. Overall platform score

| Dimension | Weight | Score |
|-----------|--------|-------|
| Core browser UX | 25% | 8.5 |
| Specialist modules | 25% | 6.8 |
| Agent ergonomics | 20% | 6.0 |
| Reliability | 20% | 6.0 |
| Packaging / install | 10% | 9.0 |

**Weighted overall: 7.2 / 10**

The platform is **meaningfully ahead of generic browser MCPs** for frontend engineering (form probe, verify, design snapshot, component search, coordination). It is **not yet a turnkey SEO or full-resource solution** out of the box.

---

## 10. Prioritized roadmap (from testing only)

| Priority | Item | Trigger |
|----------|------|---------|
| **P0** | Fix MCP resource exposure in Cursor | agent-guide fetch failed |
| **P0** | SEO audit timeout / partial results | 90s fail, no data |
| **P0** | Prevent stdio hangs (code_context, integrate) | 7+ min blocked |
| **P1** | Font + pattern resource providers | HTTP 400 / not implemented |
| **P1** | `repo_root` onboarding in install + Cursor config | missing_artifact stops coordinator |
| **P1** | Observe payload size controls | ~1 MB responses |
| **P2** | Coordinator cluster stability | context jumps on search |
| **P2** | SEO param aliases (`url` → `website_url`) | validation error observed |
| **P2** | Session lifecycle docs + session_end nudges | long sessions hang |

---

## Appendix A — Tools invoked (complete list)

| Tool | ok | Notes |
|------|-----|-------|
| `perception_health` | ✅ | |
| `perception_flow_describe` | ✅ | |
| `perception_seo_status` | ✅ | |
| `perception_session_start` | ✅ | |
| `perception_navigate_and_observe` | ✅ | |
| `perception_probe_form` | ✅ | |
| `perception_verify` | ✅ | |
| `perception_probe_guards` | ✅ | earlier session |
| `perception_auth_gate` | ✅ | |
| `perception_search_components` | ✅ | |
| `perception_plan_component_search` | ✅ | |
| `perception_resource_icon_search` | ✅ | |
| `perception_resource_search` | ✅ | |
| `perception_resource_pattern_search` | ⚠️ | empty |
| `perception_resource_font_search` | ⚠️ | empty |
| `perception_build_design_snapshot` | ✅ | |
| `perception_design_review` | ✅ | |
| `perception_coordinator_briefing` | ✅ | |
| `perception_inspiration_discover` | ✅ | earlier session |
| `perception_figma_status` | ✅ | earlier session |
| `perception_seo_audit` | ❌ | timeout |
| `perception_code_context` | ❌ | hang |
| `perception_integrate_component` | ⚠️ | ok:true degraded (6ms); needs repo_root + preview_url |
| `perception://agent-guide` | ❌ | resource not found |
| `perception://seo-guide` | ❌ | resource not found |

## Appendix B — Recommended retest procedure

To reproduce without hangs:

1. Restart MCP server in Cursor (toggle off/on).
2. Run **one browser tool at a time**; wait for response before next call.
3. Use config: `"args": ["--from", "frontend-mcp==1.0.1", "frontend-mcp"]`
4. Sequence: health → session_start → observe → probe_form → verify → (optional design/SEO).
5. Avoid parallel `CallMcpTool` batches during browser sessions.
6. Set `FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT` to your app repo for code_context and PDG.

---

*All conclusions derived from live `user-frontend-mcp` tool responses during 2026-07-12/13 testing sessions on `frontend-mcp` v1.0.1.*
