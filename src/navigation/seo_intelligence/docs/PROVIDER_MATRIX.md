# SEO Intelligence — Provider Matrix

**Policy:** 100% free-first. User-owned data preferred. No paid SEO SaaS.

## P0 — Core

| Provider | API | Auth | User data | Status |
|----------|-----|------|-----------|--------|
| Google Search Console | Search Console API v1 | OAuth 2.0 | Yes | ✅ live |
| Google Analytics 4 | GA4 Data API | OAuth 2.0 | Yes | ✅ live |
| LibreCrawl | Self-hosted HTTP | Local URL | No | ✅ live |
| Lighthouse / PSI | CLI + PSI v5 | Optional key | No | ✅ live |

## P1 — Evidence enrichment

| Provider | Role | Status |
|----------|------|--------|
| Browser Intelligence | Rendering, hydration, JS errors via `scan_id` | ✅ live |
| **OpenSEO** | GSC mirror (free); keyword/SERP/backlink (paid gated) | ✅ partial |

## P2 — Optional

| Provider | Role | Status |
|----------|------|--------|
| Bing Webmaster Tools | Secondary search console | 📋 research |

## OpenSEO (optional provider)

| Aspect | Detail |
|--------|--------|
| App cost | Free (MIT, self-hostable) |
| Data cost | DataForSEO pay-as-you-go for keyword/SERP/backlink features |
| Hard dependency | **No** — module works without OpenSEO |
| Planner blocks | technical_crawl, core_web_vitals, rendering_verification |
| Paid gate | `allow_paid_providers` on audit request |

See `OPENSEO_PROVIDER.md`.

## Do NOT build

| Capability | Reason |
|------------|--------|
| Keyword database | Infrastructure cost; solved by GSC queries |
| Backlink index | Requires web-scale crawl |
| SERP database | Requires continuous scraping |
| Custom internet crawler | Use LibreCrawl locally |

## Official sources

| Provider | Documentation |
|----------|---------------|
| Search Console API | https://developers.google.com/webmaster-tools/v1/api_reference_index |
| GA4 Data API | https://developers.google.com/analytics/devguides/reporting/data/v1 |
| PageSpeed Insights | https://developers.google.com/speed/docs/insights/v5/get-started |
| LibreCrawl | https://github.com/librecrawl/librecrawl |
| OpenSEO | https://github.com/every-app/open-seo |
| Bing Webmaster | https://learn.microsoft.com/en-us/bingwebmaster/ |
