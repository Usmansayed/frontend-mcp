# Dribbble — Provider Navigation Research

**Status:** Verified via Browser Intelligence sessions (Jul 2026).  
**Integration:** Browser-only — official Dribbble API is **not** used for Inspiration Intelligence.

## Search

| Item | Value |
|------|-------|
| URL pattern | `https://dribbble.com/search/{query_slug}` |
| Slug rules | Lowercase, spaces → hyphens, strip special chars |
| Example | `saas landing page` → `/search/saas-landing-page` |

## DOM & selectors

| Element | Selector |
|---------|----------|
| Result cards | `li.shot-thumbnail`, `[data-thumbnail-id]` |
| Shot links | `a[href*="/shots/"]` |
| Titles | `a[aria-label^="View"]` |
| Preview images | `img[src*="cdn.dribbble.com"]` |

## Pagination & loading

- **Kind:** Infinite scroll
- **Hydration wait:** 8–10 seconds after navigation
- **Headless:** Unreliable until hydration completes; headed mode preferred

## Detail pages

- Pattern: `https://dribbble.com/shots/{shot_id}`
- Capture: browser screenshot or `og:image` from detail page

## Anti-bot

- **HTTP returns 202 + ~2KB WAF stub** — plain `urllib` cannot search; browser required
- AWS WAF on first load — passes after headed browser + ~5s hydration
- Headed browser recommended; headless often blank until hydration completes

## Root cause (diagnosed Jul 2026)

```
HTTP GET /search/saas-dashboard → 202, 2007 bytes, no /shots/ links
Headed browser + 5s wait         → 643KB HTML, 40+ shots
```

Fast mode now auto-falls back to browser when HTTP WAF stub is detected.

## Auth (browser session)

| Method | Env var | Result |
|--------|---------|--------|
| Session cookie | `DRIBBBLE_SESSION_COOKIE` | Logged-in grid in browser |
| og:image | automatic | Social preview on shot detail page |
| Screenshot | automatic | Viewport capture as last resort |

Grid images are gated for anonymous users — set `DRIBBBLE_SESSION_COOKIE` for full previews.

## Browser execution

Uses **Perception MCP browser runtime** (`SessionStore` + `scan_page`) — same stack as `perception_session_start` / `perception_navigate_and_observe`. **Headed browser always** for inspiration (`headless=false`).

Artifacts: `artifacts/inspiration_browser/{session_id}/`

See [ANTI_BOT_STRATEGY.md](../ANTI_BOT_STRATEGY.md).
