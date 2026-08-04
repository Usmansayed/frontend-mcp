# Community Discovery — Research & Strategy

**Decision:** Community Discovery is **decoupled** from Figma Console MCP and from any PAT.

## What we researched

| Approach | Result |
|----------|--------|
| Figma REST API `api.figma.com` | No Community search — files by key only, requires PAT |
| `GET /api/community/search` | 404 — not a public endpoint |
| **`GET /api/search/resources`** | **✅ Live Community keyword search (REST JSON)** — see [COMMUNITY_SEARCH_RESEARCH.md](./COMMUNITY_SEARCH_RESEARCH.md) |
| LiveGraph (`/api/livegraph`) | Internal GraphQL-over-Postgres — not used by Community search UI; ToS violation if scraped |
| Community HTML SSR | Client-rendered; search data comes from `/api/search/resources` |
| `@figma-api/community` (gridaco) | S3 archive **disabled** (`AllAccessDisabled`) — not viable for extraction |

**Conclusion:** Public keyword search goes through **`GET /api/search/resources`** (no PAT). Wire the Community Discovery Adapter HTTP backend to this endpoint after review — full evidence in [COMMUNITY_SEARCH_RESEARCH.md](./COMMUNITY_SEARCH_RESEARCH.md).

## Adapter architecture

```text
Community Intelligence (queries)
        ↓
CommunityDiscoveryService
        ↓
┌───────────────────┬────────────────────┐
│ HttpCommunityBackend │ CatalogBackend   │
│ (FIGMA_COMMUNITY_    │ (default, no PAT)│
│  SEARCH_URL)         │                  │
└───────────────────┴────────────────────┘
        ↓
CommunityDiscoveryHit (normalized metadata)
        ↓
FigmaCandidate → Candidate Intelligence → Ranking → Selection Planner
```

## Normalized metadata (`CommunityDiscoveryHit`)

- title, description, tags, author
- preview_image, community_url, file_key (when known)
- likes, downloads (when available)
- design_system, discovery_score, source_backend

## PAT usage

| Stage | PAT required? |
|-------|----------------|
| Community Discovery | **No** |
| Figma Console extraction | **Yes** (or Desktop Bridge) |

## Extending discovery

1. **Catalog** — ship `FIGMA_COMMUNITY_CATALOG_JSON` with real file keys + metadata
2. **HTTP backend** — live search via `GET /api/search/resources` (default when `FIGMA_COMMUNITY_SEARCH_URL` unset)
3. **Future backend** — add new class implementing `CommunityDiscoveryBackend` without touching providers

## Provider rule

Figma Console MCP (`southleft/figma-console-mcp`) is **extraction-only**:

- `figma_get_design_system_kit`
- `figma_get_file_data`
- `figma_get_variables`
- screenshots, styles, auto-layout context

It must **never** perform Community search, ranking, or evaluation.
