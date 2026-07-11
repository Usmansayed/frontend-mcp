# SEO Intelligence

**Status:** ✅ production_v1

## Summary

SEO Intelligence orchestrates **free-first** SEO data sources into a normalized **SEO Knowledge Graph**. The agent reasons over evidence — we do not build Ahrefs, Semrush, or internet-scale crawlers.

## Philosophy

| Build | Do not build |
|-------|--------------|
| Provider adapters | Keyword databases |
| Cross-source analysis | Backlink indexes |
| Evidence-based recommendations | SERP databases |
| Verify loop with Browser Intelligence | Custom crawlers |

## Providers (live)

| Provider | Status |
|----------|--------|
| Google Search Console | ✅ OAuth + API |
| Google Analytics 4 | ✅ OAuth + Data API |
| LibreCrawl | ✅ HTTP adapter |
| Lighthouse / PageSpeed | ✅ CLI bridge |
| Browser Intelligence | ✅ `scan_id` bridge |
| OpenSEO | ✅ optional (free GSC mirror; paid gated) |
| Bing Webmaster | 📋 optional stub |

## OpenSEO (optional)

| Aspect | Detail |
|--------|--------|
| Role | GSC mirror + paid keyword/SERP when opted in |
| Cost | App free; DataForSEO pay-as-you-go |
| Hard dependency | No |

## Module path

`src/navigation/seo_intelligence/`

## MCP tools

| Tool | Status |
|------|--------|
| `perception_seo_status` | ✅ |
| `perception_seo_connect` | ✅ Google OAuth |
| `perception_seo_audit` | ✅ full pipeline |
| `perception_seo_verify` | ✅ verification loop |
| `perception://seo-guide` | ✅ |

## Boundary

SEO Intelligence owns search performance orchestration. Browser Intelligence owns live observation. Design Sense owns UX critique. Resource Intelligence owns creative assets.
