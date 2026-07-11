# Figma Intelligence — Architecture Frozen (v1.1)

**Status:** FROZEN — Community Discovery decoupled from providers  
**PAT:** optional for search, required only for deep extraction

## Canonical pipeline

```text
Agent
  ↓
Intent
  ↓
Community Intelligence
  ↓
Community Discovery (public — no PAT)     ← Community Discovery Adapter
  ↓
Candidate Intelligence
  ↓
Ranking
  ↓
Selection Planner
  ↓
Figma Console MCP (PAT)                 ← execution provider only
  ↓
Design Extraction
  ↓
Deep Candidate Review
  ↓
Reference Registry
  ↓
Project Design Graph
  ↓
Agent
```

`Search Planner` still supplies Framework/Component hints to Community Intelligence — it does not call providers.

## Separation of concerns

| Problem | Owner | PAT? |
|---------|-------|------|
| Find Community templates | Community Discovery Adapter | No |
| Expand queries | Community Intelligence | No |
| Normalize metadata | Candidate Intelligence | No |
| Rank / select | Ranking + Selection Planner | No |
| Open file + extract design | Figma Console MCP | Yes |

## Related

- [COMMUNITY_DISCOVERY.md](./COMMUNITY_DISCOVERY.md) — research + backends
- [PIPELINE.md](./PIPELINE.md)
- ADR-021, ADR-022
