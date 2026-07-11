# One Page Love — Provider Navigation Research

**Status:** Verified Jul 2026 — HTTP reliable.

## Search

| Item | Value |
|------|-------|
| Genre | `https://onepagelove.com/genre/{query_slug}` |
| Archive fallback | `https://onepagelove.com/inspiration` |
| Detail | `https://onepagelove.com/{slug}` |

**Do not** rely on `?s=` free-text search — often returns zero results.

## DOM & selectors

| Element | Selector |
|---------|----------|
| Cards | `a[href^="https://onepagelove.com/"]` |
| Screenshots | `img[src*="assets.onepagelove.com"]` |
| Slug filter | Exclude nav paths (`/about`, `/contact`, etc.) |

## Preview CDN

```
https://assets.onepagelove.com/cdn-cgi/image/width=840,quality=85/...
```

**Critical:** `cdn-cgi/image/` params contain commas — do not split URLs on commas naively.

Medium blob tier: `width=480`, `quality=75`.

## Pagination

- Numbered pages on genre/archive listings

## HTTP

- Primary tier — no browser required for discovery
- Optional `ONEPAGELOVE_API_KEY` for structured API (future)
