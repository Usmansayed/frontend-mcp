# Behance — Provider Navigation Research

**Status:** Preliminary — adapter not yet implemented.

## Search

| Item | Value |
|------|-------|
| URL pattern | `https://www.behance.net/search/projects?search={query}` |
| Encoding | URL-encode query string |

## DOM & selectors (preliminary)

| Element | Selector |
|---------|----------|
| Project cards | `[data-project-id]`, `.Project-cover` |
| Gallery links | `a[href*="/gallery/"]` |
| Titles | `[data-project-title]`, `.Project-title` |

## Pagination & loading

- Infinite scroll on search results
- Hydration wait ~6s

## Anti-bot

- Adobe CDN; moderate rate limiting on rapid pagination

## Next steps

- Browser Intelligence sessions to validate selectors
- Implement `providers/behance/parser.py` + provider
