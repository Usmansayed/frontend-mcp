# OpenSEO Provider Integration

OpenSEO is an **optional provider** behind SEO Intelligence — not a replacement for our orchestration layer.

## Cost model

| Layer | Cost |
|-------|------|
| OpenSEO application | Free (MIT, self-hostable) |
| DataForSEO API | Pay-as-you-go per request |
| OpenRouter (SAM AI features) | Optional, separate |

**Never assume OpenSEO is 100% free.** Planner gates paid capabilities behind `allow_paid_providers`.

## When the planner uses OpenSEO

| Capability | OpenSEO used? |
|------------|---------------|
| Technical crawl | **Never** — LibreCrawl |
| Core Web Vitals | **Never** — Lighthouse + GSC + Browser |
| Rendering | **Never** — Browser Intelligence |
| Search queries | **Only if** direct GSC unavailable |
| Keyword research | After GSC; if `allow_paid_providers` |
| SERP analysis | OpenSEO primary; requires paid |
| Backlinks | OpenSEO only; no free fallback |
| Domain intelligence | OpenSEO primary; GSC fallback |

## Configuration

```text
OPENSEO_BASE_URL=http://localhost:3001
OPENSEO_MCP_URL=http://localhost:3001/mcp
OPENSEO_PROJECT_ID=...          # OpenSEO project UUID (required for tool calls)
DATAFORSEO_API_KEY=...          # on OpenSEO instance (.env), not required in MCP env
```

## MCP tools (via OpenSEO instance)

Reference: [every-app/open-seo](https://github.com/every-app/open-seo)

**Free (implemented in adapter):**

- `get_search_console_performance` — GSC clicks/impressions/CTR/position (`search_queries` fallback)
- `inspect_urls` — GSC URL inspection up to 10 URLs (`index_status` fallback)

**Paid (planner-gated; adapter stub):**

- `research_keywords`, `get_keyword_metrics`
- `get_serp_results`, `find_serp_competitors`
- `get_ranked_keywords`, `get_backlinks_profile`
- `get_rank_tracker`

Our adapter calls OpenSEO MCP — we do not embed DataForSEO directly.

## Hard dependency

**No.** If OpenSEO is unavailable, SEO Intelligence continues with GSC, GA4, LibreCrawl, Lighthouse, and Browser Intelligence.
