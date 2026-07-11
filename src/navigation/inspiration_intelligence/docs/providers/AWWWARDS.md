# Awwwards — Provider Navigation Research

**Status:** Verified Jul 2026 — `GallerySiteProvider` + browser extract.

## Search

| Item | Value |
|------|-------|
| URL pattern | `https://www.awwwards.com/websites/?search={query_slug}` |
| Browse fallback | Category filters on `/websites/` |

## DOM & selectors

| Element | Selector |
|---------|----------|
| Site cards | `a[href*="/sites/"]` |
| Detail links | `https://www.awwwards.com/sites/{slug}` |
| Preview | `img.currentSrc`, `img.src`, `img[data-src]` |

## Browser extraction

- `prefer_browser=True` — HTTP alone is unreliable
- Run `PREPARE_PAGE_SCRIPT` (cookie dismiss + scroll) before `AWWWARDS_EXTRACT`
- Hydration wait: ~6s

## Pagination

- Numbered pages on website index

## Anti-bot

- OneTrust cookie banner — dismiss before extract

## Preview URLs

- Thumbnail paths often include `thumb_440_330` — resized to medium JPEG on blob materialize via Pillow
