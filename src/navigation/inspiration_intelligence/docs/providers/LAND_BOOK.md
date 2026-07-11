# Land-book — Provider Navigation Research

**Status:** Verified Jul 2026 — browser required; browse fallback when search grid empty.

## Search

| Item | Value |
|------|-------|
| Base | `https://land-book.com` (**no www**) |
| Search | `https://land-book.com/design?search={query_slug}` |
| Browse fallback | `https://land-book.com/design/landing-page` |

## DOM & selectors

| Element | Selector |
|---------|----------|
| Design cards | `a[href*="/design/"]` |
| Detail | `https://land-book.com/design/{slug}` |
| Load more | Button matching `/load more|show more/i` |

## Browser extraction

- `LANDBOOK_EXTRACT` — click load-more up to 4×, scroll, then collect links
- `browser_required=True`, hydration ~8s
- Skip category slugs: `landing-page`, `design`, `template`, etc.

## Pagination

- **Load more** button — not infinite scroll

## Preview URLs

- Generic `og-image.webp` — skip ephemeral blobs for these
- Prefer `agent_view_url` (live design page) over image preview

## Reliability

- Lowest priority in cascade — individual cards may not expose stable preview URLs
- Browse fallback returns category-level hits when search grid is empty
