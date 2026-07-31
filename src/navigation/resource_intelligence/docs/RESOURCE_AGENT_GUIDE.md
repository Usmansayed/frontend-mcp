# Resource Agent Guide — Creative Asset Playbooks

**Audience:** MCP host agents using `perception_creative_assets` / `perception_resource_*` tools.

**Read at session start when finding icons, fonts, avatars, or stock assets:** MCP resource `perception://resource-guide`

This guide mirrors **Inspiration Intelligence** — URL-first discovery, optional ephemeral vision blobs, explicit session cleanup.

**One gateway:** Prefer `perception_creative_assets` (alias of `perception_resource_search`). Category tools (`*_icon_search`, …) are shortcuts only.

**Use often on greenfield/redesign** for core atmosphere — not optional decoration:
- **Fonts** (`font`) — display + body pairing  
- **Backgrounds / patterns** (`pattern`) — subtle textures, not flat fill  
- **Color / gradients** (`gradient`) — palette planes  
- **Graphics / illustrations** (`illustration`) — hero/empty-state art  
- **Motion** (`animation`) — micro-interactions / Lottie  
- **Icons** (`icon`) — consistent icon family  

Heavy+ episodes prefetch a multi-category `creative_kit` and may list `resources?` on the pack (advisory owed, not claim-critical). Read `card.creative_kit` / call the gateway before locking chrome.

---

## 0. Workflow (every resource task)

```text
1. perception_creative_assets   → ranked assets (pass categories for fonts/patterns/gradients/…)
   (alias: perception_resource_search)
2. perception_resource_preview  → blobs ONLY when family miss + reference image (not for in-family icons)
3. Use access_url / suggested_import for icons in family; npm/CDN URLs for fonts & graphics
4. perception_resource_session_end → delete blobs when done
```

**Icon families first:** One style set per project (Lucide, Heroicons, Tabler, Phosphor, Remix). In-family hits use `access_url` + `suggested_import` — **no blobs**.

**Family miss:** `allow_family_fallback` → broader search; or `reference_preview_url` / `perception_observe` for vision/OCR.

**Resolve family:** `icon_family` param → `RESOURCE_ICON_FAMILY` env → `.cache/resource_icon_family.json` → `package.json` → default `lucide`

**URL-first:** Prefer `access_url` for npm/CDN/API integration. Blobs only for family miss or non-icon assets (avatars).

**Commercial-only default:** Non-commercial providers (e.g. Humaaans) are excluded from the default catalog.

---

## 0b. Icon families

| family_id | npm package |
|-----------|-------------|
| lucide | lucide-react |
| heroicons | @heroicons/react |
| tabler-icons | @tabler/icons-react |
| phosphor-icons | @phosphor-icons/react |
| remix-icon | @remixicon/react |

Pass `persist_icon_family: true` to lock family for the project.

---

## 1. Live providers (MVP)

| Provider | Categories | Notes |
|----------|------------|-------|
| **Iconify** | Icons | Skips CC-BY-NC collections per asset |
| **Lucide** | Icons | Lucide prefix via Iconify API |
| **DiceBear** | Avatars | Public API preview only — self-host for production commercial |

More providers are in the seed graph; adapters roll out per `docs/ROADMAP.md`.

---

## 2. Manifest / hit fields

| Field | Use |
|-------|-----|
| `access_url` | Primary integration URL (SVG/API/npm) |
| `preview_url` | Sized preview for vision or hotlink |
| `agent_view_url` | Best URL to open (same as access_url when available) |
| `resource_blob` | Ephemeral preview file (~24h TTL) — `.svg` for icons, `.jpg` for raster |
| `blob_session_id` | Pass to `perception_resource_session_end` |
| `license_warnings` | Read before shipping — attribution, automation, self-host |
| `blob_skipped` | true when provider prohibits MCP download / automation |

---

## 3. License rules (summary)

- **Exclude from catalog:** `commercial_use=false` only
- **Automation bans:** advisory — provider stays listed, blob may be skipped
- **Attribution:** gate when `attribution_ok=false` on search request
- **Fonts:** metadata + links only — no vision blobs

---

## 4. Environment variables

```bash
RESOURCE_BLOBS=1                      # default on — ephemeral preview JPEGs
RESOURCE_BLOB_ROOT=.cache/resource_blobs
RESOURCE_SESSIONS_CACHE=.cache/resource_sessions.json
RESOURCE_BLOB_TTL_HOURS=24
RESOURCE_BLOB_MAX_WIDTH=960
RESOURCE_BLOB_JPEG_QUALITY=76
```

---

## 5. Do not

- Scrape provider sites ad-hoc — use MCP tools
- Assume CC0 without reading `license_warnings`
- Auto-fetch unDraw / Storyset when `blob_skipped=true` — use manual access_url
- Leave blob sessions open — always call `perception_resource_session_end`

---

## 6. Category hints

The search parser maps query keywords to categories:

- **icon** → Iconify, Lucide
- **avatar** → DiceBear
- **font** → Fontsource (metadata phase)
- **photo** → Pexels, Pixabay (when adapters ship)

Pass `categories: ["icon"]` to override auto-detection.
