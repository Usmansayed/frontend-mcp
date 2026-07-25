# SEO Intelligence — Architecture

## Mission

SEO Intelligence is an **AI-native SEO reasoning engine** — not a replacement for Ahrefs, Semrush, or third-party SEO applications.

Data providers supply evidence. The knowledge graph stores context. The recommendation engine correlates signals and produces traceable fixes. Browser Intelligence verifies results.

## Philosophy

| We build | We do NOT build |
|----------|-----------------|
| Evidence-driven reasoning | Hundreds of hardcoded SEO rules |
| Cross-source correlation | Keyword/backlink databases |
| Prioritized recommendations | Internet-scale crawlers |
| Closed-loop browser verification | Third-party SEO app dependencies |
| Structured agent context | Unsupported conclusions |

**Evidence providers only:** Google Search Console, Google Analytics 4, LibreCrawl, Lighthouse, Browser Intelligence.

## Two-tier modes

| Mode | When | Auth | Providers |
|------|------|------|-----------|
| **Development** (default) | Building a website | None | Browser Intelligence + AI Visibility (derived) |
| **Professional** | User asks to optimize with live search data | Google OAuth on demand | GSC, GA4, LibreCrawl, Lighthouse, Browser Intelligence |

```text
# Development (default) — frictionless while coding
perception_observe → scan_id
perception_seo_audit_start { "website_url": "...", "scan_id": "..." }

# Professional — after user requests optimization
perception_seo_connect { "action": "connect_google", ... }
perception_seo_audit_start { "website_url": "...", "mode": "professional" }
perception_seo_audit_poll { "audit_job_id": "..." }
```

## Pipeline

```text
Website
  ↓
Evidence Collection (providers)
  ↓
Evidence Normalizer
  ↓
SEO Knowledge Graph
  ↓
Evidence Correlation + Opportunity Detection
  ↓
AI Visibility Adapter (derived AI-readiness evidence)
  ↓
AI Recommendation Engine (structured reasoning context)
  ↓
Verification Plan (Browser Intelligence)
  ↓
Agent (apply fix → verify → mark verified)
```

**AI Visibility layer.** After providers collect evidence, the AI Visibility
adapter runs analyzers documented in
[`../ai_visibility/docs/ANALYZER_SOURCES.md`](../ai_visibility/docs/ANALYZER_SOURCES.md)
and emits `ai_visibility` evidence. Every analyzer is grounded in Google's
public AI search guidance. See the
[AI Visibility agent guide](../ai_visibility/docs/AI_VISIBILITY_AGENT_GUIDE.md).

## Intelligence stages

### 1. Evidence collection

Planner orchestrates providers only — **no SEO logic in the planner**.

### 2. Evidence correlation

Correlation-first analysis across providers:

| Sources | Output |
|---------|--------|
| Search Console + LibreCrawl | Why pages aren't indexed |
| Search Console + Lighthouse | Poor rankings caused by CWV |
| LibreCrawl + Browser | Rendering issue preventing indexing |
| Analytics + Search Console | Traffic drop explanation |

### 3. AI reasoning

Audit results include `reasoning_context` — structured JSON for the agent:

```json
{
  "gsc": "...",
  "ga4": "...",
  "crawl": "...",
  "browser": "...",
  "lighthouse": "...",
  "correlations": "...",
  "knowledge_graph": "...",
  "history": "..."
}
```

Every recommendation includes: title, root cause, evidence used, confidence, priority, business impact, implementation steps, verification steps.

### 4. Verification

Browser Intelligence verifies fixes after apply. Recommendations support closed-loop verification via `perception_seo_verify`.

## Provider strategy

| Provider | Tier | Auth | Role |
|----------|------|------|------|
| Google Search Console | P0 | OAuth | Search performance + index health |
| Google Analytics 4 | P0 | OAuth | Traffic, landing pages, conversions |
| LibreCrawl | P0 | Local URL | Technical crawl |
| Lighthouse / PSI | P0 | Optional API key | CWV, performance, SEO audits |
| Browser Intelligence | P0 | scan_id | Rendering, DOM, console, metadata |
| Bing Webmaster | P2 | OAuth/API key | Optional second search console |

## SEO Knowledge Graph

Stores evidence, recommendations, verification history, relationships, and confidence. Continuously improves future reasoning.

Node types: `Website`, `Pages`, `Queries`, `Issues`, `Opportunities`, `Recommendations`, `VerificationStatus`.

## Module boundaries

| Module | Owns |
|--------|------|
| **SEO Intelligence** | Evidence orchestration, graph, correlation, recommendations |
| **Browser Intelligence** | Live page observation, DOM, screenshots, verification |
| **Frontend Quality** | Console, network, audits |
| **Design Sense** | UX critique — not SEO rankings |

## Environment

```text
SEO_GRAPH_PATH=.cache/seo_graph.json
LIBRECRAWL_BASE_URL=http://localhost:5001
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
PAGESPEED_API_KEY=...          # optional
BING_WEBMASTER_API_KEY=...     # optional
```

See `AUTHENTICATION.md` and `COMPANION_SERVICES.md`.
