# SEO Intelligence

**Status:** 📋 architecture_v1 (research + scaffold)

## Summary

SEO Intelligence orchestrates **free-first** SEO data sources into a normalized **SEO Knowledge Graph**. The agent reasons over evidence — we do not build Ahrefs, Semrush, or internet-scale crawlers.

## Philosophy

| Build | Do not build |
|-------|--------------|
| Provider adapters | Keyword databases |
| Cross-source analysis | Backlink indexes |
| Evidence-based recommendations | SERP databases |
| Verify loop with Browser Intelligence | Custom crawlers |

## Providers (planned)

| Provider | Priority |
|----------|----------|
| Google Search Console | P0 |
| Google Analytics 4 | P0 |
| LibreCrawl | P0 |
| Lighthouse / PageSpeed | P0 |
| Browser Intelligence | P1 |
| Bing Webmaster | P2 (optional) |

## Module path

`src/navigation/seo_intelligence/`

## Documentation

| Doc | Path |
|-----|------|
| Architecture | `seo_intelligence/docs/ARCHITECTURE.md` |
| Agent guide | `seo_intelligence/docs/SEO_AGENT_GUIDE.md` |
| Provider matrix | `seo_intelligence/docs/PROVIDER_MATRIX.md` |
| Knowledge graph | `seo_intelligence/docs/KNOWLEDGE_GRAPH_SCHEMA.md` |
| Roadmap | `seo_intelligence/docs/ROADMAP.md` |
| Research | `research/seo_intelligence/README.md` |

## MCP tools (architecture phase)

| Tool | Status |
|------|--------|
| `perception_seo_status` | ✅ scaffold |
| `perception_seo_audit` | ✅ scaffold (stubs until Phase 1) |
| `perception://seo-guide` | ✅ |

## Boundary

SEO Intelligence owns search performance orchestration. Browser Intelligence owns live observation. Design Sense owns UX critique. Resource Intelligence owns creative assets.
