# SEO Intelligence — Provider Matrix

**Policy:** Five evidence providers only. User-owned data preferred. AI-native reasoning — not third-party SEO apps.

## P0 — Core evidence providers

| Provider | API | Auth | User data | Status |
|----------|-----|------|-----------|--------|
| Google Search Console | Search Console API v1 | OAuth 2.0 | Yes | ✅ live |
| Google Analytics 4 | GA4 Data API | OAuth 2.0 | Yes | ✅ live |
| LibreCrawl | Self-hosted HTTP | Local URL | No | ✅ live |
| Lighthouse / PSI | CLI + PSI v5 | Optional key | No | ✅ live |
| Browser Intelligence | Visual browser scan | scan_id | No | ✅ live |

## P2 — Optional

| Provider | Role | Status |
|----------|------|--------|
| Bing Webmaster Tools | Secondary search console (on-demand) | ✅ live |

## Do NOT build

| Capability | Reason |
|------------|--------|
| Keyword database | Use GSC query evidence + opportunity detection |
| Backlink index | Requires web-scale crawl |
| SERP database | Requires continuous scraping |
| Third-party SEO apps | Reasoning engine is our product |
| Custom internet crawler | Use LibreCrawl locally |

## Official sources

| Provider | Documentation |
|----------|---------------|
| Search Console API | https://developers.google.com/webmaster-tools/v1/api_reference_index |
| GA4 Data API | https://developers.google.com/analytics/devguides/reporting/data/v1 |
| PageSpeed Insights | https://developers.google.com/speed/docs/insights/v5/get-started |
| LibreCrawl | https://github.com/librecrawl/librecrawl |
| Bing Webmaster | https://learn.microsoft.com/en-us/bingwebmaster/ |
