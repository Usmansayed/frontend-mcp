# SEO Intelligence — Research Notes

Architecture phase research checklist before provider implementation.

## Google Search Console API

- **API:** Search Console API v1
- **Auth:** OAuth 2.0 (user account)
- **Key endpoints:** `searchanalytics.query`, `urlInspection.index`, `sitemaps.list`, `sites.list`
- **Rate limits:** Google API quotas per Cloud project
- **Normalize to:** `SeoEvidenceKind.SEARCH_QUERY`, `INDEX_STATUS`, `CRAWL_ISSUE`, `CORE_WEB_VITAL`

## Google Analytics 4 Data API

- **API:** `analyticsdata.googleapis.com` v1
- **Auth:** OAuth 2.0 (same Google Cloud project as GSC recommended)
- **Key reports:** sessions, users, landing page, traffic source, conversions
- **Normalize to:** `TRAFFIC_METRIC`, landing page metadata on `pages` nodes

## LibreCrawl

- **Do not** embed a crawler in MCP
- **Adapter** calls user/CI LibreCrawl HTTP API
- **Normalize:** broken links, redirects, canonicals, robots, schema, internal links, status codes

## Lighthouse / PageSpeed Insights

- **Local:** `lighthouse` CLI JSON output
- **Remote:** PSI v5 `runPagespeed` endpoint
- **Normalize:** performance score, SEO score, CWV metrics (LCP, INP, CLS)

## Browser Intelligence bridge

- Input: `scan_id` from ScanRegistry
- Extract: `agent_summary.blocking`, console errors, visual_insights, hydration signals
- **Normalize to:** `RENDERING_ISSUE`

## Out of scope (confirmed)

- Ahrefs / Semrush / Moz APIs
- Custom SERP scraping
- Backlink discovery crawlers
