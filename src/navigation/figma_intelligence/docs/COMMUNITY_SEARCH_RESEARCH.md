# Figma Community Search — Research Report

**Date:** 2026-07-11  
**Method:** Frontend Perception Browser Intelligence + live network capture  
**Status:** Evidence complete — **do not implement provider wiring until review**

---

## Executive summary

Figma Community keyword search is **server-side REST JSON**, not public GraphQL and not client-only filtering.

| Finding | Result |
|---------|--------|
| Primary search endpoint | `GET https://www.figma.com/api/search/resources` |
| GraphQL / LiveGraph for search | **Not used** in the Community search UI flow |
| Auth for search | **Not required** (works unauthenticated) |
| Stable for production adapter | **Yes for discovery metadata**; detail/file APIs need WAF session |
| `@figma-api/community` | **Not viable** — S3 archive disabled (`AllAccessDisabled`) |
| REST `file_key` in search | **Not returned** — use `content_id` (Community file ID) |

**Recommended architecture:**

```text
Community Intelligence
  → Community Search Adapter (GET /api/search/resources)
  → Community File Resolver (GET /api/resources/hub_files/{content_id})
  → Candidate Intelligence → Ranking → Selection Planner
  → Figma Console MCP / PAT (optional deep extraction)
```

---

## Research workflow

### Browser Intelligence (Frontend Perception MCP)

1. Session bootstrap: `perception_session_start({ base_url: "https://www.figma.com" })`
2. Navigate: `perception_navigate_and_observe` → `https://www.figma.com/community`
3. Search queries executed: dashboard, navbar, saas, pricing, login, landing page, analytics
4. Network observation via CDP + Playwright cross-validation

### Observations

| Tool | Figma Community access |
|------|------------------------|
| **Playwright MCP** | Works — full page + network |
| **Perception MCP (headless default)** | CloudFront **403** on first load |
| **Perception MCP (headless: false + 8s wait)** | Page renders; network buffer often empty on first paint |
| **Bare Python `urllib`** | Search API works without cookies |

**Browser Intelligence gaps discovered:**

1. **WAF / bot detection** — `browser_use` default profile triggers CloudFront 403 on figma.com
2. **Slow SPA hydration** — observe before WAF token + React mount returns blank DOM
3. **Network ring buffer** — search XHR may fire before CDP attach or outside observe window; need `wait_for_network_idle` or post-action `perception_network_get`

---

## Request flow (search)

```text
User types query in Community search bar
  → URL: /community/search?query={q}&resource_type=files&sort_by=relevancy&...
  → Browser issues parallel GETs:

     1. /api/search/resources?query={q}&resource_type=design_template,ui_kit,...&caller=search_page
     2. /api/search/resources?query={q}&resource_type=plugin,weave_app&include_content=true
     3. /api/search/resources?query={q}&resource_type=widget&...
     4. /api/search/resources?query={q}&resource_type=oauth_app&...
     5. /api/search/hub_profiles?query={q}&max_num_results=50

  → UI merges tab results (Files, Plugins, Widgets, Creators)
```

**Homepage browse (non-search):**

```text
GET /api/resources?sort_by=all_time&resource_type=design_template&caller=homepage&page_size=6&query_id={uuid}
GET /api/community_categories_v2/all
```

**File detail (after clicking a result):**

```text
GET /api/resources/hub_files/{content_id}?include_full_category=true
GET /api/resources/{resource_uuid}/comments?page_size=60
GET embed.figma.com/community/file/{content_id}/canvas  (preview embed, 302)
POST embed.figma.com/community/file/{content_id}/image/batch  (rendered thumbnails)
```

---

## Primary endpoint: `/api/search/resources`

### Method

`GET` — REST JSON (not GraphQL)

### Example

```http
GET /api/search/resources?query=saas&price=all&creators=all&sort_by=relevancy&resource_type=design_template,ui_kit,prototype&session_id=unattributed&include_content=false&caller=search_page&include_full_category=false&include_tags=false&queryId={uuid} HTTP/1.1
Host: www.figma.com
Accept: application/json
User-Agent: Mozilla/5.0 ...
Referer: https://www.figma.com/community/search  (optional)
x-csrf-bypass: yes  (sent by Figma web app; optional for search)
```

### Query parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `query` | Search text | `dashboard` |
| `resource_type` | Comma-separated types | `design_template,ui_kit,prototype` |
| `sort_by` | Ranking | `relevancy`, `all_time` |
| `price` | Filter | `all` |
| `creators` | Filter | `all` |
| `session_id` | Analytics | `unattributed` (logged out) |
| `caller` | Telemetry | `search_page` |
| `include_content` | Embed plugin manifest | `false` for files |
| `include_full_category` | Category tree | `false` |
| `include_tags` | Tag payload | `false` / `true` |
| `queryId` | Client correlation UUID | any UUID-like string |

### Response envelope

```json
{
  "error": false,
  "status": 200,
  "meta": {
    "total_hits": 1336,
    "results": [
      { "model": { "...": "..." } }
    ]
  },
  "i18n": {}
}
```

Each `results[]` entry wraps a **`model`** object (Hub resource).

### Model fields (discovery-relevant)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Hub **resource_id** (e.g. `27d74790-c100-4c56-ba71-a2d35f55f1f6`) |
| `content_id` | string | **Community file ID** — use in `/community/file/{content_id}` URLs |
| `name` | string | Title |
| `description` | HTML string | Often rich HTML |
| `resource_type` | enum | `design_template`, `ui_kit`, `plugin`, … |
| `like_count` | int | Likes |
| `user_count` | int | Uses / duplicates (shown as downloads in UI) |
| `view_count` | int | Often 0 in search |
| `created_at` | ISO8601 | |
| `community_rdp_url` | URL | Canonical community link |
| `thumbnail_url` | URL | CDN preview |
| `thumbnail_src_set` | object | 160 / 800 / 1200 widths |
| `creator` | object | `id`, `handle`, `img_url` |
| `publisher` | object | Profile metadata |
| `editor_types` | string[] | e.g. `["design"]` |
| `tags_v2` | object | Tags when `include_tags=true` |
| `category_id` | string? | Often null in search |
| `metadata` | object | Extension slot |

### Fields **not** in search response

| Missing | Implication |
|---------|-------------|
| REST `file_key` (22-char) | Cannot call `api.figma.com/v1/files/{key}` directly from search |
| `library_key` | Only on hub_files detail |
| Component tree | Requires embed / PAT / Desktop Bridge |
| Slug | URL uses numeric `content_id` + optional name segment |

---

## Secondary endpoint: `/api/resources/hub_files/{content_id}`

Richer metadata for a single Community file.

### Access

| Context | Result |
|---------|--------|
| Browser with cookies + WAF token | **200** |
| Bare `urllib` (no session) | **403 Forbidden** |

### Additional fields vs search

| Field | Notes |
|-------|-------|
| `content.hub_file.library_key` | Internal library identifier (`lk-…`) — **not** REST file_key |
| `content.hub_file.duplicate_count` | Download count |
| `content.hub_file.versions` | Version map with `client_meta` |
| `tags` | Array (when populated) |
| `category_slug` / `parent_category_slug` | Category breadcrumbs |
| `carousel_media` | Extra preview assets |
| `comment_count` | |

---

## Search query evidence (2026-07-11)

| Query | `total_hits` (sample) | Top result `content_id` |
|-------|----------------------|-------------------------|
| dashboard | 100+ returned | `1015169662427839322` |
| navbar | 100+ | `1291236026031262016` |
| saas | 1336 | `1202426685198179521` |
| pricing | 100+ | `1135161493190764209` |
| login | 100+ | `1019155319918719973` |
| landing page | 100+ | `1350836811191304513` |
| analytics | 100+ | `1152266255337829742` |

Reproducible POC: `python scripts/research_figma_community_search.py`

---

## Stability & programmatic access

### Can endpoints be called programmatically?

| Endpoint | Without browser | With browser session |
|----------|-----------------|---------------------|
| `/api/search/resources` | **Yes** — tested with User-Agent + Accept only | Yes |
| `/api/resources/hub_files/{id}` | **No** — 403 | Yes (credentials + WAF) |
| `/api/resources` (homepage) | Likely yes (same family) | Yes |
| `embed.figma.com/.../canvas` | Redirect / session-bound | Yes |

### Authentication

- Search: **no login required** (`session_id=unattributed`)
- Statsig ruleset: 401 without session (feature flags only)
- No PAT for Community discovery

### Cookies / WAF

- Page load runs **AWS WAF** challenge: `*.token.awswaf.com/.../verify`
- Search API bypasses WAF; hub_files does not
- `x-csrf-bypass: yes` header used by Figma SPA (optional for search)

### Rate limits

- No `Retry-After` or explicit rate-limit headers observed
- Response `cache-control: private, must-revalidate, max-age=300` (5 min CDN cache)
- Practical cap: **~100 results per resource_type batch** per request

### Anti-bot

- CloudFront 403 for automated browsers (Perception default profile)
- WAF token required for some endpoints
- `@figma-api/community` S3 bucket returns `AllAccessDisabled`

---

## `@figma-api/community` evaluation

**Package:** `@figma-api/community@0.0.7` (gridaco)  
**POC:** `node scripts/poc_figma_community_api.mjs`

### How it works

Fetches pre-archived files from:

```text
https://figma-community-files.s3.us-west-1.amazonaws.com/{communityFileId}/file.json.gz
```

### Test results (2026-07-11)

| File ID | Result |
|---------|--------|
| `1015169662427839322` (live search hit) | **403 AllAccessDisabled** |
| `1035203688168086460` (documented example) | **403 AllAccessDisabled** |

### Conclusions

| Question | Answer |
|----------|--------|
| Accepts Community file IDs? | Yes — numeric `content_id` from search |
| Requires file keys? | No |
| Can retrieve document tree? | **Archive disabled** — no longer |
| Can retrieve images? | **Archive disabled** |
| Replace Figma Console for public files? | **No** — not production viable |

---

## Identifier model (Community File Resolver)

```text
search hit
  resource_id (UUID)     → hub resource key, comments API
  content_id (numeric)   → community URL, hub_files API, embed canvas
  library_key (lk-…)     → hub_files only; internal, not REST file_key
```

Mapping to Figma REST `file_key` requires **user duplication** or **Desktop Bridge** — not available from public Community APIs alone.

---

## Browser Intelligence improvements (recommended)

Before relying on Perception for external SaaS research:

1. **External site profile** — realistic Chrome UA, `--disable-blink-features=AutomationControlled`, default `headless: false` for non-localhost
2. **WAF bootstrap step** — navigate + wait for `awswaf.com/verify` before observe
3. **Network wait hook** — `wait_for_load_state('networkidle')` or filter `api/search` before finalize scan
4. **Export JSON bodies** — auto-capture `application/json` responses matching `/api/search/` to artifacts

---

## Recommendation

### Build around discovered endpoint — **YES**

Use `GET /api/search/resources` as the **Community Search Adapter** HTTP backend:

- No PAT for discovery
- Stable JSON schema with rich metadata
- `content_id` + `community_rdp_url` sufficient for Candidate Intelligence
- Pair with `hub_files` resolver when browser session or cached WAF cookies available

### Use `@figma-api/community` — **NO**

Archive bucket disabled. Do not depend on gridaco S3 for extraction.

### Figma Console MCP — **optional downstream**

Still required for deep kit extraction (tokens, components, variables) on owned/duplicated files.

### Do not use LiveGraph — **confirmed**

Internal GraphQL-over-Postgres; not used by Community search UI; ToS risk.

---

## Deliverables index

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Full search mechanism doc | This file |
| 2 | Endpoints + flow | § Request flow |
| 3 | Response schema | § Model fields |
| 4 | Production stability | § Stability |
| 5 | `@figma-api/community` POC | `scripts/poc_figma_community_api.mjs` |
| 6 | Search API POC | `scripts/research_figma_community_search.py` |
| 7 | Recommendation | § Recommendation |

**Next step (after review):** Wire `HttpCommunityBackend` parser to `meta.results[].model` shape — **not started per research gate.**
