# Frontend MCP — Architecture & Reference Integration Plan

> Master plan for becoming the default frontend MCP for coding agents.  
> See [architecture.md](./architecture.md) for current vs target layout.

## Goal

Build the **ultimate Frontend MCP** for AI coding agents — a complete frontend perception, debugging, verification, and workflow platform.

This is **not** BrowserTools MCP, a Playwright wrapper, or a browser automation product.

---

## Reference policy

Do **not** copy BrowserTools into our runtime.

1. Reference clone: `references/browser-tools-mcp/` (study only).
2. Never copy its architecture (extension + middleware + MCP).
3. Never depend on its extension or `browser-tools-server`.
4. Recreate capabilities via **CDP + Browser Use + managed Chromium**.

---

## Our architecture

| Layer | Technology |
|-------|------------|
| Protocol | MCP (stdio) |
| Browser | Browser Use → Chromium via CDP |
| Sessions | Managed (`perception_session_*`); future attach-to-Chrome |
| Brain | Host agent (Cursor/Claude) |
| Server LLM | None |

**Excluded:** browser extension, WebSocket middleware, separate browser-tools-server.

---

## BrowserTools capabilities → our reimplementation

### Console (planned module: `console/`)

- Full log capture: log/info/debug/warn/error
- Stack traces, source mapping, exceptions
- Filtering, session history
- **CDP:** `Runtime`, `Log`

**Today:** `dev_insights` captures errors/warnings/exceptions during observe — partial.

### Network (planned module: `network/`)

- Request lifecycle, timing, headers, bodies
- Redirects, failures, MIME, HAR export
- Slow/duplicate detection, API grouping, GraphQL hints
- **CDP:** `Network`

**Today:** failures, API paths, slow requests in `dev_insights` — partial.

### Screenshots (module: `visual/`)

- Viewport, full-page, element, annotated
- Side-by-side, heatmap, before/after

**Today:** ✅ implemented in `visual_capture.py`, `visual_diff.py`, inline MCP images.

### Audits (planned module: `audits/`)

Tools:

- `perception_audit_accessibility`
- `perception_audit_performance`
- `perception_audit_seo`
- `perception_audit_best_practices`

May use Lighthouse internally; expose **our** report schema.

**Today:** not implemented (reference: `references/browser-tools-mcp/browser-tools-server/lighthouse/`).

### Full diagnosis (planned module: `reports/`)

Tool: `perception_full_diagnosis`

Pipeline:

```
Observe → Console → Network → Accessibility → Performance → Visual → Verification → Final Report
```

**Today:** agent follows `AGENT_GUIDE` manually; orchestration tool not built.

### Reports

Never return raw logs by default. Structured sections:

- Summary, Blocking, Warnings
- Console, Network, Visual, Performance
- Suggested fixes (facts only — no LLM in server)
- Artifacts (scan_ids, screenshots, diffs)

**Today:** `agent_summary` + `visual` block + scan resources — foundation exists.

---

## Existing features (must remain first-class)

| Area | Tools / modules |
|------|-----------------|
| Observe | `perception_navigate_and_observe`, `perception_observe` |
| Navigate | `perception_navigate` |
| Actions | `perception_execute_script`, `perception_execute_actions` |
| Verification | `perception_verify` |
| Regression | `perception_diff` |
| Visual | annotated screenshots, visual_insights, inline images |
| Forms | `perception_probe_form` |
| Guards | `perception_probe_guards` |
| Auth | `perception_auth_gate` |
| State | `perception_state_*` |
| Flows | `perception_flow_describe` |
| Code ↔ UI | `perception_code_context` |

---

## Design principles

Every feature must be:

- Modular, loosely coupled, testable
- Deterministic (no LLM in MCP server)
- Documented in same PR as code
- Easy to extend via interfaces

Prefer composition over tight coupling.

---

## Documentation discipline

When adding a major feature:

1. Update `docs/features/<area>.md`
2. Update `docs/roadmap.md`
3. Update `docs/tool_reference.md` if new MCP tool
4. Record decisions in `docs/design_decisions.md` if architectural

Deferred work must say **why** in roadmap.

---

## Comparison with BrowserTools

See [features/comparison_browser_tools.md](./features/comparison_browser_tools.md).
