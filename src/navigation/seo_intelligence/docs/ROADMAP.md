# SEO Intelligence — Roadmap

## Phase 0 — Research & Architecture ✅ (Jul 2026)

- [x] Module scaffold `seo_intelligence/`
- [x] Provider matrix (free-first)
- [x] SEO Knowledge Graph schema
- [x] Models + service facade + orchestrator skeleton
- [x] Provider protocol + research stubs
- [x] Cross-analysis + recommendation + verification skeleton
- [x] MCP status + guide resource
- [ ] Per-provider deep research notes (Phase 0.5)

## Phase 1 — User-owned data (P0)

- [ ] Google Search Console OAuth + evidence normalizers
- [ ] GA4 Data API OAuth + landing page reports
- [ ] Connection status in graph
- [ ] `perception_seo_audit` returns real GSC/GA4 evidence

## Phase 2 — Technical SEO (P0)

- [ ] LibreCrawl adapter (local instance only)
- [ ] Lighthouse CLI + PageSpeed Insights adapter
- [ ] Issue normalization into graph

## Phase 3 — Intelligence depth

- [ ] Browser Intelligence SEO bridge (`scan_id` → rendering evidence)
- [ ] Cross-analysis rules (indexing, CTR, CWV correlations)
- [ ] Recommendation confidence scoring
- [ ] Verification status tracking in graph

## Phase 4 — MCP production

- [ ] `perception_seo_connect` (OAuth flow guidance)
- [ ] `perception_seo_verify` (re-audit after fix)
- [ ] Contract tests with mock provider payloads

## Phase 5 — Optional + freeze

- [ ] Bing Webmaster adapter
- [ ] Freeze module at ~85 — coordination layer across modules > more SEO providers

## Explicitly out of scope

- Keyword databases
- Backlink crawlers
- SERP rank trackers
- Paid SEO APIs (Ahrefs, Semrush, Moz API)
