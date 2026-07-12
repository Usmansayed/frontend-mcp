# SEO Intelligence

**Status:** ✅ production_v1 — AI-native recommendation architecture

## Summary

SEO Intelligence is an **AI-native SEO reasoning engine**. Five evidence providers feed a normalized knowledge graph. The recommendation engine correlates signals, detects opportunities, and produces traceable fixes verified by Browser Intelligence.

We do not build Ahrefs, Semrush, third-party SEO apps, or internet-scale crawlers.

## Philosophy

| Build | Do not build |
|-------|--------------|
| Evidence correlation | Hardcoded rule engines |
| AI reasoning context | Keyword/backlink databases |
| Opportunity detection | SERP databases |
| Browser verification loop | Third-party SEO app dependencies |

## Evidence providers

| Provider | Status |
|----------|--------|
| Google Search Console | ✅ OAuth + API |
| Google Analytics 4 | ✅ OAuth + Data API |
| LibreCrawl | ✅ core companion (auto-started) |
| Lighthouse / PageSpeed | ✅ CLI bridge |
| Browser Intelligence | ✅ `scan_id` bridge |
| Bing Webmaster | ✅ optional OAuth/API (on-demand) |

## Pipeline

### Development (default)

```text
Browser + Lighthouse + LibreCrawl → Knowledge Graph → Dev best practices → Recommendations
```

### Professional (on demand)

```text
GSC + GA4 + technical providers → Knowledge Graph → Correlation + opportunities → Recommendations
```

Audit results include `reasoning_context` for structured agent root-cause analysis and `recommendations` with root cause, business impact, and verification steps.

## Core companion

LibreCrawl auto-starts as a native background process before audits. See `COMPANION_SERVICES.md`.

| Service | Default URL |
|---------|-------------|
| LibreCrawl | `http://localhost:5001` |

## Module path

`src/navigation/seo_intelligence/`

## Onboarding (website URL only)

```text
Website URL → SEO Intelligence ready

Google / Bing OAuth only when user requests provider-specific analysis
```

## MCP tools

| Tool | Status |
|------|--------|
| `perception_seo_status` | ✅ |
| `perception_seo_connect` | ✅ setup + on-demand OAuth |
| `perception_seo_audit` | ✅ full pipeline + reasoning context |
| `perception_seo_verify` | ✅ closed-loop verification |
| `perception://seo-guide` | ✅ |
