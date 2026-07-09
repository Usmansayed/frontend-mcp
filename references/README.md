# Reference implementations (read-only)

This folder contains **external projects studied for feature ideas only**.

## Policy

| Rule | Meaning |
|------|---------|
| **Reference only** | Do not import, depend on, or copy-paste from these repos into `src/` |
| **No extension** | We do not ship or require Chrome extensions from references |
| **No middleware** | We do not run reference Node servers as part of our MCP |
| **Recreate in our stack** | Reimplement capabilities via CDP + Browser Use + our module layout |

## Contents

| Path | Purpose |
|------|---------|
| `browser-tools-mcp/` | [AgentDeskAI/browser-tools-mcp](https://github.com/AgentDeskAI/browser-tools-mcp) — console/network/Lighthouse patterns (project inactive; study `browser-tools-mcp/mcp-server.ts`, `browser-tools-server/lighthouse/`) |

## When studying a reference

1. Read what **user-facing capability** it provides.
2. Find the **data shape** returned to the LLM.
3. Reimplement under `src/navigation/` using **CDP** (`navigation/perception/cdp_hub.py`) and our **report envelope**.
4. Document in `docs/features/` and update `docs/roadmap.md`.

## Updating references

```bash
cd references/browser-tools-mcp && git pull
```

Shallow clone: `git clone --depth 1 https://github.com/AgentDeskAI/browser-tools-mcp.git references/browser-tools-mcp`
