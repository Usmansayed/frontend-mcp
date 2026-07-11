# Inspiration Agent Guide — Provider Playbooks

**Audience:** MCP host agents using `perception_inspiration_*` tools.

**Read at session start when gathering UI inspiration:** MCP resource `perception://inspiration-guide`

This guide encodes **how each gallery site is navigated**, **how preview URLs are obtained**, and **what fails in production**. The Python module implements these rules — follow the tools, not ad-hoc scraping.

---

## 0. Workflow (every inspiration task)

```text
1. perception_inspiration_discover   → ranked candidates (fast, URLs + scores)
2. perception_inspiration_collect    → URLs + ephemeral vision blobs (when you need images)
3. Use agent_view_url for live pages; inspiration_blob for vision
4. perception_inspiration_session_end → delete blobs when design work is done
```

**URL-first:** Prefer `agent_view_url` (live page). Use `inspiration_blob` only for quick visual reference — blobs expire (~24h) and are deleted on session end.

**Provider priority (early stop):** Dribbble → Behance → One Page Love → Awwwards → SiteInspire → Godly → Land-book

---

## 1. Dribbble

| Item | Value |
|------|-------|
| Search | `https://dribbble.com/search/{query_slug}` |
| Detail | `https://dribbble.com/shots/{shot_id}` |
| HTTP | **Fails** — returns 202 WAF stub (~2KB). Browser required. |
| Headed browser | Required; wait 8–10s hydration |
| Grid selectors | `li.shot-thumbnail`, `a[href*="/shots/"]`, `img[src*="cdn.dribbble.com"]` |

**Preview URL ladder:**
1. `DRIBBBLE_SESSION_COOKIE` env → full grid images when logged in
2. `og:image` from shot detail page
3. Perception browser screenshot (last resort)

```bash
DRIBBBLE_SESSION_COOKIE="_dribbble_session=...; ..."
INSPIRATION_HEADLESS=false
```

---

## 2. Behance

| Item | Value |
|------|-------|
| Search | `https://www.behance.net/search/projects?search={query}` |
| Detail | `https://www.behance.net/gallery/{id}/...` |
| HTTP | **Works** — preferred tier |
| Preview | `project_modules/1400/` → medium: `project_modules/800/` |

**Selectors:** `a[href*="/gallery/"]`, gallery id regex `/gallery/(\d+)`

---

## 3. One Page Love

| Item | Value |
|------|-------|
| Search | `/genre/{query_slug}` (not `?s=` — often empty) |
| Fallback | `https://onepagelove.com/inspiration` |
| Detail | `https://onepagelove.com/{slug}` |
| HTTP | **Works** |
| Preview CDN | `assets.onepagelove.com/cdn-cgi/image/width=...,quality=...` |

**Critical:** CDN URLs contain commas inside `cdn-cgi/image/` params — never split srcset on commas blindly. Medium blob tier uses `width=480`, `quality=75`.

**Filter:** Require screenshot asset near card; skip nav links (`/about`, etc.).

---

## 4. Awwwards

| Item | Value |
|------|-------|
| Search | `https://www.awwwards.com/websites/?search={query_slug}` |
| Detail | `https://www.awwwards.com/sites/{slug}` |
| HTTP | Unreliable — **browser preferred** |
| Extract | `a[href*="/sites/"]`, img `currentSrc` / `data-src` |
| Cookie banner | Dismiss OneTrust / accept buttons before extract |

**Hydration:** ~6s after load. Uses `AWWWARDS_EXTRACT` script (scroll + cookie prep).

---

## 5. SiteInspire

| Item | Value |
|------|-------|
| Search | `https://www.siteinspire.com/search?q={query}` |
| Detail | `https://www.siteinspire.com/website/{id}` |
| Browser | Preferred — lazy grid |
| Preview CDN | `width=960` → medium: `width=640` |

---

## 6. Godly (redirects to recent.design)

| Item | Value |
|------|-------|
| Entry | `https://godly.website` → redirects to **recent.design** |
| Cards | `a[href*="/i/"]` — **not** `/website/` |
| Detail | `https://recent.design/i/{id}-{slug}` |
| Browser | Required; ~7s hydration |
| Search | Client-side filter after catalog load |

**Do not** use outdated `/website/{slug}` paths from early research docs.

---

## 7. Land-book

| Item | Value |
|------|-------|
| Base | `https://land-book.com` (**no www**) |
| Browse fallback | `https://land-book.com/design/landing-page` when search grid empty |
| Detail | `https://land-book.com/design/{slug}` |
| Browser | **Required** — load-more + scroll |
| Extract | Click "Load more" up to 4×, then `a[href*="/design/"]` |
| Previews | Often generic `og-image.webp` — **skip blob** for these |

**Skip slugs:** `landing-page`, `design`, category pages (see `LANDBOOK_EXTRACT` skip set).

Individual design cards may not expose stable preview URLs — use `agent_view_url` (live page) over image blobs.

---

## 8. Environment variables

```bash
INSPIRATION_HEADLESS=false      # headed browser (default)
INSPIRATION_FAST=1              # early stop when enough hits
INSPIRATION_FORCE=1             # run all providers (probes/tests)
INSPIRATION_BLOBS=1             # materialize blobs in pipeline (default on)
INSPIRATION_BLOB_TTL_HOURS=24   # auto-cleanup safety net
DRIBBBLE_SESSION_COOKIE=...     # optional full Dribbble previews
```

---

## 9. Manifest fields (collect output)

| Field | Use |
|-------|-----|
| `url` | Canonical page URL |
| `agent_view_url` | Best URL for agent to open |
| `preview_url` | CDN / og:image when available |
| `inspiration_blob` | Ephemeral medium JPEG for vision |
| `blob_session_id` | Pass to `perception_inspiration_session_end` |
| `fetch_tier` | `http` \| `browser` \| `screenshot` |

---

## 10. Anti-bot rules

- HTTP first where reliable (Behance, One Page Love)
- Headed Perception browser fallback on WAF / empty grids
- Cookie dismiss + scroll before DOM extract (`PREPARE_PAGE_SCRIPT`)
- Rate limits + early stop — do not hammer all seven sites every run
- Never loop login — inspiration sites are read-only public galleries

See `inspiration_intelligence/docs/ANTI_BOT_STRATEGY.md` for full policy.
