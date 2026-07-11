# Resource Graph — Schema

The Resource Graph stores **knowledge about providers and assets** — not copyrighted asset binaries.

Persisted at: `.cache/resource_graph/` (JSON/SQLite TBD) + seed data in `graph/seed.py`.

---

## Node types

```text
ResourceGraph
├── ProviderNode          # iconify, pexels, fontsource, …
├── CollectionNode        # lucide, mdi, fa6-solid (within Iconify)
├── AssetNode             # individual icon, photo, font family
├── LicenseNode           # normalized SPDX + flags
├── TagNode               # style, industry, format
└── CategoryNode          # icon, photo, font, …
```

---

## ProviderNode

```json
{
  "provider_id": "iconify",
  "display_name": "Iconify",
  "categories": ["icon"],
  "priority_tier": 0,
  "api": {
    "available": true,
    "base_url": "https://api.iconify.design",
    "auth": "none",
    "rate_limit": "fair use; self-host recommended"
  },
  "self_host": {
    "supported": true,
    "methods": ["npm @iconify/api", "docker"]
  },
  "license_profile_id": "license:iconify-platform",
  "maintenance": {
    "status": "active",
    "last_verified": "2026-07-11",
    "source_url": "https://iconify.design/docs/api/"
  },
  "excluded": false,
  "adapter_status": "planned"
}
```

---

## CollectionNode (optional)

For aggregators (Iconify collections, DiceBear styles, Fontsource families):

```json
{
  "collection_id": "iconify:lucide",
  "provider_id": "iconify",
  "name": "Lucide",
  "asset_count": 1541,
  "license_profile_id": "license:isc",
  "tags": ["outline", "minimal"],
  "framework_compat": ["react", "vue", "svelte"]
}
```

---

## AssetNode

```json
{
  "asset_id": "iconify:lucide:arrow-right",
  "provider_id": "iconify",
  "collection_id": "iconify:lucide",
  "category": "icon",
  "title": "arrow-right",
  "tags": ["arrow", "navigation"],
  "style": ["outline", "minimal"],
  "format": "svg",
  "preview_url": "https://api.iconify.design/lucide/arrow-right.svg",
  "access_url": "https://api.iconify.design/lucide/arrow-right.svg",
  "license_profile_id": "license:isc",
  "commercial_ok": true,
  "attribution_required": false,
  "popularity": 0.92,
  "quality_score": 0.88,
  "updated_at": "2026-07-01T00:00:00Z"
}
```

**Note:** Graph may cache asset metadata from search results with TTL — never mirror full provider catalogs unless license permits.

---

## LicenseNode

See `LICENSE_INTELLIGENCE.md` — referenced by `license_profile_id`.

```json
{
  "license_profile_id": "license:cc-by-4.0",
  "spdx_id": "CC-BY-4.0",
  "commercial_use": true,
  "attribution_required": true,
  "redistribution_allowed": true,
  "mcp_download_allowed": true,
  "ai_training_allowed": false,
  "dataset_use_allowed": false,
  "api_automation_allowed": true,
  "attribution_template": "© {author} — {license_url}",
  "source_url": "https://creativecommons.org/licenses/by/4.0/"
}
```

---

## Edges

| Edge | Meaning |
|------|---------|
| `provider → category` | Provider serves category |
| `provider → collection` | Aggregator contains collection |
| `collection → asset` | Membership |
| `asset → license` | Effective license |
| `asset → tag` | Style/topic |
| `asset → compatible_framework` | React, Tailwind, etc. |

---

## Query API (internal)

```python
graph.find_providers(category="icon", commercial_required=True)
graph.get_provider("iconify")
graph.upsert_search_results(provider_id, assets)  # TTL cache
graph.license_for_asset(asset_id) -> LicenseProfile
```

---

## Sync strategy

| Source | Sync |
|--------|------|
| Seed providers | `graph/seed.py` — manual revalidation |
| Iconify collections | Periodic API `collections` endpoint |
| Fontsource | npm registry metadata scrape |
| Simple Icons | npm package `simple-icons` metadata |
| Pexels / Unsplash | **No bulk ingest** — search-time only |
| Open Doodles / Lucide | Static git release hash |

---

## What we never store

- Full photo binaries
- Complete icon font dumps
- Scraped illustration packs
- Rive `.riv` files (link to editor/export only)

Ephemeral preview blobs (optional future) follow Inspiration Intelligence TTL pattern — not graph persistence.
