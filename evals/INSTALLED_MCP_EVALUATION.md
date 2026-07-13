# Installed MCP Evaluation Report — `frontend-mcp` v1.0.0

**Date:** 2026-07-13  
**Method:** Hands-on evaluation via Cursor MCP server **`frontend-mcp`** (`user-frontend-mcp`) — no local `src/`, no contract runners, no dev scripts.  
**Install path observed by runtime:** `uv` cache (`C:\Users\usman\AppData\Local\uv\cache\archive-v0\...\Lib\`)  
**Target app:** `http://localhost:5173` (sandbox dev server running)

---

## Executive summary

**The installed MCP does not work for end users in its current PyPI/uvx form.**

Every tool invocation and every bundled resource read failed before returning a v1.0 envelope. The server is **reachable** (tools are listed in Cursor), but **no workflow could be exercised**.

| Category | Tools attempted | Passed | Failed |
|----------|-----------------|--------|--------|
| Core browser | `perception_health`, `perception_session_start`, `perception_flow_describe` | 0 | 3 |
| SEO | `perception_seo_status` | 0 | 1 |
| Components | `perception_search_components` | 0 | 1 |
| MCP resources | `perception://agent-guide`, `perception://seo-guide` | 0 | 2 |
| Design / Resource / AI Visibility / Coordination / E2E | Not reached — blocked by universal tool failure | 0 | — |

**Blocking error (all tools):**

```
[Errno 2] No such file or directory:
...\Lib\coordination_layer\runtime\manifest.json
```

**Production readiness (installed MCP):** **Not ready** — P0 packaging defect.

---

## 1. Overall assessment

v1.0.0 passes extensive **developer-side** validation (handler contract tests, coordination simulate suite, execution runtime EVW) but **fails immediately** when consumed as an installed MCP through Cursor/`uvx`.

The failure mode is catastrophic but narrow: the **Coordinator Bridge** loads runtime artifacts from `coordination_layer/runtime/` on every tool call, and that directory **is not included** in the published wheel. End users never get past the first tool call.

Resources (`perception://agent-guide`, etc.) also failed with **“MCP resource not found”**, so the host agent cannot load playbooks at session start — a second packaging gap.

**What this means:** An end user following README/Cursor setup correctly still gets a **non-functional MCP**. Dev validation gave false confidence because tests import handlers directly or run from a full monorepo checkout where `coordination_layer/` exists on disk.

---

## 2. Feature-by-feature review

### 2.1 Core browser workflows — **Not testable (blocked)**

| Tool | Result |
|------|--------|
| `perception_health` | Error: missing `coordination_layer/runtime/manifest.json` |
| `perception_session_start` | Same |
| `perception_flow_describe` | Same |

**Expected workflow (AGENT_GUIDE §1):** health → session_start → observe → verify  
**Actual:** Cannot complete step 1.

**Strengths:** N/A from installed MCP (not exercised).  
**Weaknesses:** Universal hard failure before handler logic runs.

---

### 2.2 Design workflows — **Not testable (blocked)**

Tools not reached: `perception_build_design_snapshot`, `perception_design_review`, `perception_consistency_audit`, `perception_design_graph_*`, etc.

---

### 2.3 Component workflows — **Not testable (blocked)**

| Tool | Result |
|------|--------|
| `perception_search_components` | Error: missing manifest |

`perception_plan_component_search`, `perception_integrate_component` not attempted — same failure expected.

---

### 2.4 Resource workflows — **Not testable (blocked)**

`perception_resource_search`, `perception_resource_preview`, etc. not reached.

---

### 2.5 SEO workflows — **Not testable (blocked)**

| Tool | Result |
|------|--------|
| `perception_seo_status` | Error: missing manifest |

`perception_seo_audit`, `perception_seo_connect`, `perception_seo_query`, `perception_seo_verify` not reached.

---

### 2.6 AI Visibility workflows — **Not testable (blocked)**

Typically exercised via `perception_seo_audit` with `include_ai_visibility`. Not reached.

---

### 2.7 Coordination layer — **Fails at load time**

Coordinator tools exist in the tool list (`perception_coordinator_episode_start`, `perception_coordinator_briefing`, `perception_coordinator_apply_envelope`) but could not be invoked — the bridge crashes while loading **R0–R11 manifest** before any coordinator logic runs.

**Observation:** Coordination is not optional on the installed path; it blocks all tools rather than degrading gracefully.

---

### 2.8 Execution runtime — **Not observable via MCP**

Execution runtime (retry, idempotency, correlation IDs, `data.execution`) is infrastructure inside the server. It cannot be evaluated when no tool returns an envelope.

---

### 2.9 Cross-module & E2E engineering tasks — **Not testable (blocked)**

No session, observe, verify, form probe, or multi-step flow could be run.

---

### 2.10 MCP resources — **Failed**

| Resource | Result |
|----------|--------|
| `perception://agent-guide` | MCP resource not found |
| `perception://seo-guide` | MCP resource not found |

Host agents are instructed to read `perception://agent-guide` at session start; that path is broken on the installed server.

---

## 3. Strengths (platform design — from tool surface, not runtime)

These are visible from the **tool catalog** and prior dev validation, not from successful installed-MCP calls:

| Area | Strength |
|------|----------|
| Tool breadth | 70+ tools covering browser, design, components, resources, SEO, Figma, coordination |
| Contract discipline | v1.0 envelope design, `agent_summary.blocking` vs advisory, no planning hints in server |
| Playbook model | AGENT_GUIDE-driven host-agent loop (observe → reason → act → verify) |
| Module boundaries | Specialist modules behind thin MCP handlers |
| Coordination (design) | Deterministic planner beneath host LLM; frozen CVW baseline |
| Execution runtime (design) | Reliability/idempotency/observability as infrastructure layer |

---

## 4. Weaknesses (evidence-based only)

| # | Weakness | Evidence |
|---|----------|----------|
| P0 | **Runtime artifacts not shipped in wheel** | Every tool: `manifest.json` missing under `coordination_layer/runtime/` in uv cache |
| P0 | **MCP resources not served** | `perception://agent-guide` and `perception://seo-guide` not found |
| P1 | **No graceful degradation** | Missing manifest aborts all tools; `COORDINATION_DISABLED` not documented for end-user Cursor config |
| P1 | **Dev vs install validation gap** | Contract tests call handlers directly; never caught PyPI layout |
| P2 | **uvx vs pip ambiguity** | Cursor `uvx` path uses ephemeral cache; errors reference uv archive, not site-packages |

---

## 5. Improvement recommendations

### P0 — Must fix before claiming production MCP

1. **Bundle `coordination_layer/runtime/`** (R0–R11 YAML + `manifest.json`) inside `frontend-perception-engine` wheel via `package-data` or vendor into `navigation/coordination_intelligence/artifacts/`.
2. **Verify resources** on installed package: `perception://agent-guide`, module guides, eval docs.
3. **Add installed-MCP smoke test** to release gate: spawn `frontend-mcp` (or `uvx --from frontend-mcp frontend-mcp`), `tools/call perception_health`, assert `contract_version == "1.0"` — **not** handler-only tests.
4. **Republish** as v1.0.1 after fix; re-run this evaluation checklist.

### P1 — Resilience

5. If `manifest.json` is missing, bridge should set `coordinator.integrated: false` and **still return handler envelope** (degraded mode), not raise.
6. Document `COORDINATION_DISABLED=1` in README for users who want browser-only MCP.

### P2 — UX

7. `frontend-mcp-install` should print Cursor config using server name `frontend-mcp` and verify post-install smoke.
8. Publish troubleshooting section: “all tools fail with manifest.json” → upgrade to fixed version.

---

## 6. Architecture observations

```
Host LLM (Cursor)
    ↓ MCP stdio
frontend-mcp (PyPI)
    ↓
navigation.mcp.server
    ↓ every tool call
CoordinatorBridge → loads coordination_layer/runtime/manifest.json  ← FAILS HERE (not in wheel)
    ↓
Handler → envelope v1.0
```

The architecture is sound for a monorepo checkout. The **packaging boundary** is wrong: `coordination_layer/` lives at repo root but is runtime-critical and was never added to setuptools `package-data`.

Execution runtime and coordination intelligence **cannot be evaluated** through the installed MCP until envelopes flow again.

---

## 7. Production readiness

| Gate | Dev repo (prior sign-off) | Installed MCP (this eval) |
|------|---------------------------|---------------------------|
| Handler contract tests | PASS | N/A (different path) |
| CVW 14/14 simulate | PASS | N/A |
| EVW 10/10 | PASS | N/A |
| MCP stdio / Cursor tools | Not in production gate | **FAIL 0/6** |
| Resources | Not gated on install | **FAIL 0/2** |
| End-user usable | Assumed | **No** |

**Verdict:** Platform v1.0.0 is **not production-ready as an installed MCP**. Republish required.

---

## 8. Module scorecard (installed MCP — hands-on)

Scores reflect **actual tool results** on `frontend-mcp` today. `NT` = not testable (blocked).

| Module | Score | Notes |
|--------|-------|-------|
| Core browser | **0 / 10** | All calls failed at bridge |
| Design intelligence | **NT** | Blocked |
| Component intelligence | **0 / 10** | search_components failed |
| Resource intelligence | **NT** | Blocked |
| SEO intelligence | **0 / 10** | seo_status failed |
| AI Visibility | **NT** | Blocked |
| Figma intelligence | **NT** | Blocked |
| Inspiration intelligence | **NT** | Blocked |
| Coordination layer | **0 / 10** | Crashes loading manifest |
| Execution runtime | **NT** | No envelopes returned |
| MCP resources / guides | **0 / 10** | agent-guide, seo-guide not found |
| Reliability / UX | **1 / 10** | Server connects; tools list; then hard fail |

---

## 9. Overall platform score (installed MCP)

| Dimension | Score |
|-----------|-------|
| **Installed MCP usability** | **0.5 / 10** |
| **Tool catalog completeness** | **8 / 10** (visible, not runnable) |
| **Packaging / distribution** | **1 / 10** |
| **Production readiness (end user)** | **Fail** |

**Weighted overall (installed path only): 1.0 / 10**

---

## 10. Prioritized roadmap (from this evaluation only)

| Priority | Item | Rationale |
|----------|------|-----------|
| **P0** | Ship `coordination_layer/runtime` in wheel | Unblocks 100% of tools |
| **P0** | Fix MCP resources on installed package | Unblocks AGENT_GUIDE at session start |
| **P0** | Add PyPI smoke test to CI/release gate | Prevent recurrence |
| **P0** | Release v1.0.1 and re-run this eval | Confirm fix |
| **P1** | Graceful coordination degrade | Avoid total outage on missing artifacts |
| **P1** | Re-test all workflow categories after P0 | This document’s §2 checklist |
| **P2** | Performance baselines on installed MCP | Not measured — no successful calls |

---

## Appendix: Tools invoked (raw)

```
perception_health          → manifest.json missing
perception_flow_describe   → manifest.json missing
perception_session_start   → manifest.json missing
perception_seo_status      → manifest.json missing
perception_search_components → manifest.json missing
perception://agent-guide   → resource not found
perception://seo-guide     → resource not found
```

---

## Next step for you

After a packaging fix is published, re-run this same checklist through Cursor **`frontend-mcp`** only. Until `perception_health` returns a v1.0 envelope with `ok` true/false (not a Python traceback), no feature-level scoring is meaningful.
