# Figma Intelligence — Agent Guide

Figma Intelligence is a **connection + coordination layer** between Frontend Perception MCP and the user's Figma workspace. It orchestrates **southleft/figma-console-mcp** — it does not reimplement Figma.

## Responsibility

> Connect to the user's Figma account and provide structured design context to the rest of the MCP.

**Not in scope here:**

| Need | Module |
|------|--------|
| Public design inspiration | Inspiration Intelligence |
| Component search / install | Component Intelligence |
| Design critique | Design Sense Intelligence |
| Icons, fonts, photos | Resource Intelligence |

## Tools

| Tool | When |
|------|------|
| `perception_figma_status` | Check connection, session, MCP health |
| `perception_figma_connect` | Connect with PAT (once), check status, disconnect |
| `perception_figma_context` | Normalized file, pages, frames, components, variables, styles, tokens, selection |

Read this guide (`perception://figma-guide`) before calling Figma tools.

## Connect flow

1. User: "Connect my Figma account"
2. Ask for **Personal Access Token** (Figma → Settings → Security → Personal access tokens)
3. `perception_figma_connect` with `pat`
4. On success, token is stored locally — **do not ask again** unless validation fails
5. `perception_figma_context` with `file_url` or `file_key` for the target file

## Context flow

```
User request
  → perception_figma_context (optional file_url, refresh)
  → Figma Intelligence (cache / session / adapter)
  → Figma Console MCP
  → Normalized FigmaDesignContext
  → Agent reasons + other intelligence modules
```

Set session before context when needed:

- `file_url` / `file_key` — active file
- `page_id` — active page
- `frame_id` — active frame
- `selection_node_ids` — selection override
- `refresh: true` — bypass cache

## Architecture (internal)

| Layer | Role |
|-------|------|
| Connection Manager | PAT connect, validate, store, reuse |
| Session Manager | Active file, page, frame, selection |
| Figma Console MCP Adapter | Clean internal API — MCP tool names hidden |
| Context Normalizer | `FigmaDesignContext` models |
| Design Cache | TTL cache; invalidate on session change |
| Coordination Layer | Cache vs refresh vs MCP |
| Health Monitor | Connection + console status |

## Examples

- **Analyze current file:** connect → context with `file_url` → pass tokens/components to Consistency or Design Sense
- **Implement frame:** context with `frame_id` → codebase + component intelligence
- **Extract tokens:** context → use `tokens` / `variables` arrays
- **Compare design vs code:** context + `perception_observe` + Design Sense / Consistency

## Legacy pipeline

Community discovery, ranking, and duplication APIs remain in `FigmaIntelligenceService` for backward compatibility. New agent workflows should use **connect + context** only.
