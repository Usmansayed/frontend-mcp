# MCP UX Improvements Report — v1.1.6

**Date:** 2026-07-13  
**Scope:** Agent discoverability, communication, and documentation — no architecture redesign.

---

## Summary

| Priority | Status | Impact |
|----------|--------|--------|
| P1 Tool discoverability | Done | 83 tools grouped, sorted, `_meta.perception.group` on each tool |
| P2 Tool descriptions | Done | What/when/before/next prefix on every tool |
| P3 Schemas | Partial+ | Common examples on session_id, scan_id, repo_root; detail enum doc; claim/verify examples |
| P4 Degraded messages | Done | `agent_guidance[]` with `agent_action` on every error/degraded envelope |
| P5 Agent guidance | Done | AGENT_GUIDE §1b, resolver guide, server instructions |
| P6 Health | Done | Versions, browser flag, `recommended_next_tool` |
| P7 Communication | Done | Shorter actionable guidance via `agent_guidance` |
| P8 Documentation | Partial | Core guides updated; full doc audit is ongoing |
| P9 Evaluation | Done | 13 unit + 74/74 contract PASS |

---

## Improvements made

### 1. Tool catalog (`src/navigation/mcp/tool_catalog.py`)

**Why:** 83 tools overwhelm agents without structure (eval score: discoverability 5/10).

**What:**
- 11 groups: Session, Browser, Quality, Resolver, Component, Design, SEO, Resources, Inspiration, Figma, Diagnostics, Coordinator
- `tools/list` sorted by `group_order` then name
- Each tool: `_meta.perception.group`, enriched description, schema patches

**Before:**
```
description: "Playbook: session bootstrap (AGENT_GUIDE §1). Check dev server..."
```

**After:**
```
description: "[Session] Ping dev server; confirm MCP envelope. | When: First call every task. | Before: — | Next: perception_session_start | ..."
_meta: { "perception": { "group": "Session", "group_order": 10 } }
```

**Measured impact:** Agents can scan `[Browser]` / `[Resolver]` prefixes; clients can filter on `_meta.perception.group`.

---

### 2. Agent guidance (`src/navigation/mcp/agent_guidance.py`)

**Why:** `degraded: ["integration_plan_only"]` gave no recovery path.

**What:** `attach_guidance()` adds `agent_guidance` to envelopes:

```json
{
  "ok": false,
  "error": "session_id required",
  "agent_guidance": [
    {
      "code": "error",
      "message": "session_id required",
      "agent_action": "Call perception_session_start first; save session_id for browser tools."
    }
  ]
}
```

**Before:** Error string only.  
**After:** Deterministic `agent_action` for 40+ degraded codes and common errors.

---

### 3. Envelope (`src/navigation/core/envelope.py`)

**Why:** Central place to attach guidance without touching every handler.

**What:** `make_envelope()` auto-attaches `agent_guidance` when `error` or `degraded` present.

**Measured impact:** All tools benefit; contract tests still pass (additive field).

---

### 4. Health (`handle_health`)

**Why:** Agents could not confirm installed version after Cursor restart.

**Before:**
```json
{ "data": { "reachable": true, "status": 200 } }
```

**After:**
```json
{
  "data": {
    "reachable": true,
    "status": 200,
    "server_version": "1.1.6",
    "package_version": "1.1.6",
    "frontend_mcp_version": "1.1.6",
    "browser_runtime_available": true,
    "recommended_next_tool": "perception_session_start"
  }
}
```

---

### 5. Server instructions + AGENT_GUIDE

**Why:** Serial tool use and `detail` levels were eval P0 gaps.

**Added:**
- §1b Observe detail levels table (summary_only / full / metadata_only)
- Scan reuse list (SEO, diff, correlate_live)
- Serial execution rule (bold in instructions)
- Tool groups reference in MCP instructions

---

### 6. Resolver guide

**Why:** Agents failed stdio tests by passing wrong `claim` shape.

**Added:** `detail: "full"` note in standard loop step 1.

---

## Test results (v1.1.6 local)

| Suite | Result |
|-------|--------|
| `tests/test_mcp_agent_ux.py` | 6/6 PASS |
| `tests/test_mcp_envelope_contract.py` | 7/7 PASS |
| `src/run_mcp_contract_tests.py` | 74/74 PASS |

---

## Remaining opportunities (future, not in this change)

| Item | Priority | Notes |
|------|----------|-------|
| `perception://tool-catalog` resource | P1 | Markdown index grouped by task |
| Per-tool `examples` on all 83 schemas | P2 | Started with common fields only |
| `agent_summary.next_suggested_calls` | P2 | Facts-only hints, not LLM |
| Full docs audit (every `docs/*.md`) | P2 | Partial — canonical guides updated |
| Publish v1.1.6 to PyPI | Release | Local only until publish |
| Cursor `_meta` UI for groups | Client | Depends on MCP client support |

---

## Files changed

- `src/navigation/mcp/tool_catalog.py` (new)
- `src/navigation/mcp/agent_guidance.py` (new)
- `src/navigation/core/envelope.py`
- `src/navigation/mcp/tools.py`
- `src/navigation/mcp/handlers.py`
- `src/navigation/mcp/server.py`
- `src/navigation/mcp/instructions.py`
- `src/navigation/mcp/AGENT_GUIDE.md`
- `src/navigation/resolver_intelligence/docs/RESOLVER_AGENT_GUIDE.md`
- `tests/test_mcp_agent_ux.py` (new)
- `pyproject.toml`, `packages/frontend-mcp/*` → **1.1.6**

---

## Bottom line

Runtime architecture unchanged. Agents get **grouped tools**, **workflow-oriented descriptions**, **actionable errors**, and **richer health** — addressing the main gaps from the v1.1.5 evaluation without removing or simplifying any capability.
