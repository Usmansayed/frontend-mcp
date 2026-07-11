# Resource Intelligence — MCP Tool Specification

**Status:** Spec only — not wired in `navigation/mcp/` yet.

**Future resource:** `perception://resource-guide` (license + provider playbook)

---

## Primary tool

### `perception_resource_search`

Universal asset search across categories.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | **required** | e.g. `minimal arrow icon`, `saas hero photo`, `inter font` |
| `categories` | string[] | inferred | `icon`, `photo`, `font`, `logo`, `avatar`, `illustration`, `svg`, `3d`, `mockup`, `animation`, `gradient`, `pattern` |
| `commercial_required` | bool | `true` | Reject non-commercial licenses |
| `attribution_ok` | bool | `true` | Allow CC-BY / API attribution requirements |
| `prefer_svg` | bool | `true` | Prefer vector formats |
| `prefer_self_hosted` | bool | `false` | Prefer npm/git over hotlink APIs |
| `max_results` | int | `12` | |
| `provider_preference` | string | optional | e.g. `lucide`, `pexels` |

**Returns:**

```json
{
  "resource_recommendation": {
    "assets": [/* ResourceAssetRef */],
    "providers_queried": ["iconify", "lucide"],
    "license_warnings": [],
    "degraded": []
  },
  "agent_summary": {
    "query": "...",
    "categories": ["icon"],
    "top_assets": [],
    "license_summary": {},
    "advisory": ["Read license_warnings before shipping to production"]
  }
}
```

---

## Category shortcuts

Thin wrappers over `perception_resource_search` with fixed `categories` and tuned defaults.

| Tool | Category | Example query |
|------|----------|---------------|
| `perception_icon_search` | icon | `settings gear outline` |
| `perception_illustration_search` | illustration | `team collaboration empty state` |
| `perception_photo_search` | photo | `modern office workspace` |
| `perception_font_search` | font | `geometric sans similar to inter` |
| `perception_logo_search` | logo | `github stripe vercel` |
| `perception_avatar_search` | avatar | `deterministic user placeholder` |
| `perception_pattern_search` | pattern | `subtle dots background` |
| `perception_gradient_search` | gradient | `purple blue sunset` |
| `perception_mockup_search` | mockup | `iphone app screenshot frame` |
| `perception_animation_search` | animation | `loading spinner lottie` |

Optional future: `perception_3d_search`, `perception_svg_search`

---

## License query tool (phase 2)

### `perception_resource_license_check`

| Param | Type | Description |
|-------|------|-------------|
| `provider_id` | string | e.g. `pexels` |
| `asset_id` | string | optional specific asset |
| `use_case` | string | `commercial_web`, `ai_training`, `redistribution` |

Returns structured allow/deny + official source links.

---

## Session / ephemeral previews (phase 3)

Mirror Inspiration Intelligence blobs — optional, not permanent storage:

- `perception_resource_preview` — medium-quality ephemeral preview for vision
- `perception_resource_session_end` — cleanup

---

## MCP instructions addition (planned)

```text
§14 Resource assets → perception://resource-guide
  perception_resource_search before ad-hoc asset URLs
  Always read license_warnings; never assume CC0
  unDraw / Storyset: no automated fetch
```

---

## Handler pattern

```python
async def handle_resource_search(arguments: dict) -> dict:
    from navigation.resource_intelligence import ResourceDiscoveryRequest, ResourceIntelligenceService
    service = ResourceIntelligenceService()
    result = await service.search(ResourceDiscoveryRequest(...))
    return make_envelope("perception_resource_search", ok=bool(result.assets), data={...})
```

Register in `mcp/tools.py`, `mcp/handlers.py`, `mcp/server.py` during Phase 5.

---

## Contract tests

- Mock provider adapter returns fixed assets
- License gate blocks `commercial_required=false` on CC-BY-NC
- `undraw` / `storyset` stay in catalog; adapters emit `automation_prohibited_by_provider` warning (no auto-fetch)
- Resource guide resource readable
