# SiteInspire — Provider Navigation Research

**Status:** Preliminary — adapter not yet implemented.

## Search

| Item | Value |
|------|-------|
| URL pattern | `https://www.siteinspire.com/search?q={query}` |
| Fallback | Tag/category URLs (`/websites/tag/{tag}`) |

## DOM & selectors (preliminary)

| Element | Selector |
|---------|----------|
| Website cards | `.website-item`, `article.website` |
| Detail links | `a[href*="/website/"]` |

## Pagination

- Numbered pages

## Loading

- Lazy-loaded thumbnails — wait for image `src` resolution

## Next steps

- Compare search vs tag browse reliability
- Implement provider adapter
