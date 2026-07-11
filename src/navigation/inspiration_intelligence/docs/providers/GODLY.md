# Godly / recent.design — Provider Navigation Research

**Status:** Verified Jul 2026 — redirects to recent.design.

## Important

`https://godly.website` **redirects** to `https://recent.design`. Card links use `/i/{id}-{slug}`, **not** `/website/{slug}`.

## Search

| Item | Value |
|------|-------|
| Entry | `https://godly.website` or `https://recent.design` |
| Search | Client-side filter after catalog hydration (`?search=` suspected) |

## DOM & selectors

| Element | Selector |
|---------|----------|
| Cards | `a[href*="/i/"]` |
| Detail | `https://recent.design/i/{id}-{slug}` |
| Preview | `img.currentSrc`, `img.src`, `img[data-src]` |

## Browser extraction

- `GODLY_EXTRACT` script in `browser/extract_scripts.py`
- `prefer_browser=True`, hydration ~7s
- Next.js — wait for grid mount

## Pagination

- Infinite scroll / client-side catalog
