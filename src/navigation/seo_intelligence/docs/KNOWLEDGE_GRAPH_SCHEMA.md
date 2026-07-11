# SEO Knowledge Graph — Schema

Version: **1**

Path: `SEO_GRAPH_PATH` (default `.cache/seo_graph.json`)

## Design principles

1. **Normalize** — store `SeoEvidenceRef`, not raw API JSON
2. **Reference** — recommendations cite `evidence_ids`
3. **No duplication** — provider payloads live in adapters during collection; graph holds canonical nodes
4. **Verification** — track fix outcomes per recommendation

## Top-level document

```json
{
  "version": 1,
  "updated_at": 1700000000,
  "website": { "url": "https://example.com", "property_url": "sc-domain:example.com" },
  "providers": { },
  "pages": { },
  "queries": { },
  "issues": { },
  "evidence": { },
  "opportunities": { },
  "recommendations": { },
  "verification": { }
}
```

## Node types

| Node | Key | Description |
|------|-----|-------------|
| Website | `website` | Audited site + GSC property |
| Pages | `pages` | Normalized page entities |
| Queries | `queries` | Search queries (from GSC) |
| Issues | `issues` | Crawl, technical, rendering issues |
| Evidence | `evidence` | All `SeoEvidenceRef` by id |
| Opportunities | `opportunities` | Derived improvement areas |
| Recommendations | `recommendations` | Evidence-linked fixes |
| Verification | `verification` | Per-recommendation verify status |

## Evidence kinds

`search_query`, `index_status`, `crawl_issue`, `core_web_vital`, `traffic_metric`, `technical_issue`, `rendering_issue`, `schema`, `internal_link`, `performance`, `opportunity`

## Cross-module links

- `evidence.metadata.scan_id` → Browser Intelligence observation
- `pages.url` → codebase routes (future Codebase Intelligence link)
- `verification.status` → `perception_verify` outcomes (future)
