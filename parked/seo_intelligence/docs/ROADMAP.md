# SEO Intelligence — Roadmap

## Phase 0 — Research & Architecture ✅ (Jul 2026)

- [x] Module scaffold `seo_intelligence/`
- [x] Provider matrix (free-first)
- [x] SEO Knowledge Graph schema
- [x] Models + service facade + orchestrator

## Phase 1 — User-owned data ✅

- [x] Google Search Console OAuth + evidence normalizers
- [x] GA4 Data API OAuth + landing page reports
- [x] Connection status probing
- [x] `perception_seo_audit` returns GSC/GA4 evidence when OAuth configured

## Phase 2 — Technical SEO ✅

- [x] LibreCrawl adapter (local instance)
- [x] Lighthouse CLI adapter (performance + SEO categories)
- [x] Issue normalization into graph

## Phase 3 — Intelligence depth ✅

- [x] Browser Intelligence SEO bridge (`scan_id` → rendering evidence)
- [x] Cross-analysis rules (indexing, CTR, CWV, technical correlations)
- [x] Recommendation confidence + fix guidance
- [x] Verification status tracking in graph

## Phase 4 — MCP production ✅

- [x] `perception_seo_connect` (Google OAuth)
- [x] `perception_seo_verify` (re-audit after fix)
- [x] Unit tests with mock provider payloads

## Phase 5 — Optional + freeze

- [x] Bing Webmaster adapter (optional OAuth/API)
- [x] AI-native recommendation pipeline (correlation, opportunities, reasoning_context)
- [ ] Freeze module at ~85 — coordination across modules > more SEO providers

## Phase 6 — AI Visibility layer ✅ (Jul 2026)

- [x] `AiVisibilityAdapter` derives `ai_visibility` evidence from collected SEO evidence
- [x] 12 analyzers grounded in Google's public AI search guidance (see `ai_visibility/docs/ANALYZER_SOURCES.md`)
- [x] `reasoning_context_v2.ai_readiness` block + `ai_visibility` recommendation category
- [x] Graph queries `ai.readiness.summary` and `page.ai_readiness`
- [x] `include_ai_visibility` flag on `perception_seo_audit`
- [x] Verification loop extended to compare derived AI evidence across audits

## Explicitly out of scope

- Keyword databases
- Backlink crawlers
- SERP rank trackers
- Paid SEO APIs (Ahrefs, Semrush, Moz API)
