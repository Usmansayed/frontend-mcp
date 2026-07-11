# Inspiration Intelligence

Public design inspiration orchestration for agents building UI.

## Scope

- Find inspiration on Dribbble, Behance, Awwwards, SiteInspire, Godly, and Land-book
- Expand queries via Community Intelligence (semantic search planning)
- Rank, select, and capture screenshots for Design Snapshot / Reference Registry

**Not in scope:** User Figma files, variables, or Community duplication — see [figma_intelligence.md](./figma_intelligence.md).

## Provider strategy

Providers are searched in priority order. Discovery stops when enough high-confidence candidates are found — lower-priority sites are skipped.

**Dribbble** uses browser-based browsing only (no official API). Set `DRIBBBLE_SESSION_COOKIE` for logged-in grid previews. Subject to Dribbble's terms of service.

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_inspiration_discover` | Fast ranked discovery (URLs + scores) |
| `perception_inspiration_collect` | Full collection + ephemeral vision blobs |
| `perception_inspiration_session_end` | Delete blob session when design work is done |

**Agent guide:** MCP resource `perception://inspiration-guide` — read before inspiration tools.  
**Playbook:** `AGENT_GUIDE.md` §13.

## Architecture

```text
Intent → Search Planner → Community Intelligence → Provider Manager
  → [providers] → Candidate Intelligence → Ranking → Selection Planner
  → Browser Intelligence (capture) → Design Snapshot → Reference Registry
```

Module path: `src/navigation/inspiration_intelligence/`

Research: `inspiration_intelligence/docs/providers/`  
Agent playbook: `inspiration_intelligence/docs/INSPIRATION_AGENT_GUIDE.md` (MCP: `perception://inspiration-guide`)  
Anti-bot & auth: `inspiration_intelligence/docs/ANTI_BOT_STRATEGY.md`
