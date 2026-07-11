# SEO Intelligence — Architecture

## Mission

SEO Intelligence is the **orchestration layer** for search performance — not a replacement for Ahrefs, Semrush, or internet-scale crawlers.

The AI agent is the brain. External tools are data providers.

## Philosophy

| We build | We do NOT build |
|----------|-----------------|
| Provider adapters | Keyword databases |
| SEO Knowledge Graph (normalized) | Backlink indexes |
| Cross-source analysis | SERP databases |
| Evidence-based recommendations | Internet-scale crawlers |
| Verification loop (observe → verify) | Paid SEO SaaS lock-in |

**100% free-first.** User-owned data (Search Console, GA4) + open tools (LibreCrawl, Lighthouse) + Browser Intelligence.

## Pipeline

```text
Website
  ↓
Planning (provider router)
  ↓
Data Collection (adapters)
  ↓
SEO Knowledge Graph (normalize)
  ↓
Cross Analysis
  ↓
Recommendation Engine
  ↓
Verification Plan
  ↓
Agent (reason + act + verify)
```

## Provider strategy

| Provider | Tier | Auth | Role |
|----------|------|------|------|
| Google Search Console | P0 | OAuth | User search performance + index health |
| Google Analytics 4 | P0 | OAuth | Traffic, landing pages, conversions |
| LibreCrawl | P0 | Local URL | Technical crawl — **do not build crawler** |
| Lighthouse / PSI | P0 | Optional API key | CWV, performance, SEO audits |
| Browser Intelligence | P1 | scan_id | Rendering, hydration, JS errors |
| Bing Webmaster | P2 | API key | Optional second search console |

## SEO Knowledge Graph

Central source of truth. **Does not duplicate raw provider payloads.**

Node types: `Website`, `Pages`, `Queries`, `Issues`, `CoreWebVitals`, `Redirects`, `IndexStatus`, `InternalLinks`, `Schema`, `Performance`, `Opportunities`, `Recommendations`, `VerificationStatus`.

See `KNOWLEDGE_GRAPH_SCHEMA.md`.

## Cross-analysis examples

| Sources | Output |
|---------|--------|
| Search Console + LibreCrawl | Why pages aren't indexed |
| Analytics + Search Console | Why CTR is falling |
| Lighthouse + Browser Intelligence | Why CWV is poor |
| Browser + LibreCrawl | Rendering problems affecting indexing |

Every recommendation **must** cite `evidence_ids`.

## Verification loop

```text
Analyze → Recommend → Apply (agent/code) → Verify (perception_verify) → Repeat
```

## Module boundaries

| Module | Owns |
|--------|------|
| **SEO Intelligence** | Search performance orchestration, SEO graph, cross-analysis |
| **Browser Intelligence** | Live page observation, DOM, screenshots |
| **Frontend Quality** | Console, network, audits (shared Lighthouse data path TBD) |
| **Design Sense** | UX critique — not SEO rankings |
| **Resource Intelligence** | Creative assets — not SEO |

Browser Intelligence is consumed via `providers/browser/` adapter — never duplicated.

## Implementation phases

| Phase | Focus |
|-------|-------|
| **0 (now)** | Architecture, models, graph schema, provider stubs, docs |
| **1** | Search Console + GA4 OAuth, evidence normalization |
| **2** | LibreCrawl + Lighthouse adapters |
| **3** | Browser SEO bridge + cross-analysis depth |
| **4** | MCP audit tools + verification automation |
| **5** | Bing optional + freeze at ~85 unless user request |

## Environment

```text
SEO_GRAPH_PATH=.cache/seo_graph.json
LIBRECRAWL_BASE_URL=http://localhost:8080
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
PAGESPEED_API_KEY=...          # optional
BING_WEBMASTER_API_KEY=...     # optional
```

See `AUTHENTICATION.md`.
