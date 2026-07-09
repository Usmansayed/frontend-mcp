# BrowserTools MCP vs Frontend Perception MCP

**BrowserTools:** `@agentdeskai/browser-tools-mcp` (reference clone: `references/browser-tools-mcp/`)  
**Status:** BrowserTools marked **inactive** by maintainers.

**Us:** `frontend-perception-engine` / `frontend-mcp` — CDP + Browser Use, no extension.

---

## Architecture

| | BrowserTools | Frontend Perception |
|---|--------------|---------------------|
| Browser connection | Chrome extension → WebSocket server → MCP | MCP → Browser Use → CDP → Chromium |
| Extra install | Extension + `browser-tools-server` | `pip install` / `uvx` only |
| LLM in stack | MCP tools only | Host agent only (MCP deterministic) |
| Production status | Inactive | Active |

---

## Feature matrix

| Capability | BrowserTools | Us (v0.2) |
|------------|--------------|-----------|
| Screenshot | ✅ | ✅ + annotated + element + inline MCP images |
| Console logs | ✅ full history, wipe | ⚠️ errors/warn during observe |
| Network XHR | ✅ bodies | ⚠️ failures/slow/API paths |
| Lighthouse a11y | ✅ | ❌ planned v0.6 |
| Lighthouse perf/SEO/BP | ✅ | ❌ planned v0.6 |
| Audit mode / Debug mode | ✅ | ❌ planned v0.7 (`perception_*_mode`) |
| Selected element inspect | ✅ via DevTools | ❌ use DOM from observe |
| Next.js audits | ✅ | 📋 backlog |
| Navigate + act on page | ❌ read-only | ✅ execute_script, execute_actions |
| Verification criteria | ❌ | ✅ `perception_verify` |
| Visual regression diff | ❌ | ✅ text + heatmap |
| Form probing | ❌ | ✅ |
| Route guard probing | ❌ | ✅ |
| Auth gate (human MFA) | ❌ | ✅ |
| State save/restore | ❌ | ✅ |
| Flow description | ❌ | ✅ |
| Code ↔ UI (`code_context`) | ❌ | ✅ |
| Structured agent_summary | partial | ✅ blocking-first |
| HAR export | ❌ | 📋 v0.5 |
| Full diagnosis report | partial (modes) | 📋 v0.7 |

---

## When to use which

**Use Frontend Perception** when:

- Building/fixing UI with an AI coding agent (observe → edit code → verify loop)
- You want zero extension setup
- You need deterministic verification and regression

**Study BrowserTools reference** when:

- Porting audit runner patterns
- Comparing console/network aggregation UX for agents

**Do not** deploy BrowserTools extension as part of our product.

---

## Philosophy

| BrowserTools | Frontend Perception |
|--------------|---------------------|
| Browser debugger for the agent | Frontend workflow platform for the agent |
| Dumps logs | Structured reports + playbooks |
| Passive observation | Observe + act + verify |

See [INTEGRATION_PLAN.md](../INTEGRATION_PLAN.md) for reimplementation plan.
