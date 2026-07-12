# Figma Intelligence

**Path:** `src/navigation/figma_intelligence/`  
**Status:** Connection + coordination layer (v2)

> **Public inspiration** lives in [inspiration_intelligence.md](./inspiration_intelligence.md). This module connects to the **user's own Figma account** and returns normalized design context.

## Philosophy

Figma Intelligence has **one responsibility**:

> Connect to the user's Figma account and provide structured design context to the rest of the MCP.

It orchestrates **southleft/figma-console-mcp** — it does not reimplement Figma.

| Concern | Owner |
|---------|--------|
| Public inspiration | Inspiration Intelligence |
| Component search / install | Component Intelligence |
| Design critique | Design Sense Intelligence |
| Creative assets | Resource Intelligence |

## Architecture

```text
User → Connect Figma → Figma Intelligence
  ├── Connection Manager      (PAT connect, validate, store)
  ├── Session Manager         (active file, page, frame, selection)
  ├── Figma Console MCP Adapter (clean internal API)
  ├── Context Normalizer      (FigmaDesignContext models)
  ├── Design Cache            (TTL, invalidate on session change)
  ├── Coordination Layer      (cache vs refresh vs MCP)
  └── Health Monitor
        ↓
  Normalized Design Context → Agent → Other Intelligence Modules
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_figma_status` | Module phase, connection, session, health |
| `perception_figma_connect` | PAT connect / status / disconnect |
| `perception_figma_context` | Normalized file, pages, frames, components, variables, styles, tokens, selection |

**Agent guide:** `perception://figma-guide`

## Authentication

1. User: "Connect my Figma account"
2. Agent prompts for PAT (Figma → Settings → Security)
3. `perception_figma_connect` with `pat`
4. Token stored locally (`.cache/figma_tokens.json` or `FIGMA_TOKEN_PATH`)
5. Never ask again unless token invalid

## Normalized models

`FigmaDesignContext` — `File`, `Page`, `Frame`, `Component`, `Variant`, `Variable`, `Style`, `Token`, `Selection`

Other modules consume these models only — never raw Figma Console MCP payloads.

## Legacy pipeline

Community discovery, ranking, extraction, and duplication remain for backward compatibility (`discover`, `run_pipeline`). New agent workflows use **connect + context** only.

## Related docs

- [FIGMA_AGENT_GUIDE.md](../src/navigation/figma_intelligence/docs/FIGMA_AGENT_GUIDE.md)
- [ARCHITECTURE.md](../src/navigation/figma_intelligence/docs/ARCHITECTURE.md) (module internals)
- ADR-023 in [design_decisions.md](./design_decisions.md)

## Sibling integration

- **Design Sense / Consistency** — critique and token comparison using normalized context
- **Component Intelligence** — implement frames with component foundations
- **Design Snapshot Engine** — optional snapshot from extracted context
