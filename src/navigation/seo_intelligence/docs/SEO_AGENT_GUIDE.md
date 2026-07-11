# SEO Intelligence — Agent Guide

Read this guide before calling `perception_seo_*` tools.

## What this module is

SEO Intelligence **orchestrates** free SEO data sources. It does not crawl the internet or sell keyword data.

## Agent loop

```text
1. perception_seo_status          — module phase + provider connections
2. Connect user accounts        — Search Console / GA4 (when Phase 1 ships)
3. perception_seo_audit         — gather evidence → graph → recommendations
4. Fix code / config            — agent applies evidence-based fixes
5. perception_observe + verify  — Browser Intelligence verifies rendering/index fixes
6. Re-audit                     — measure gains
```

## Hard rules

- **Never** recommend without `evidence_ids`.
- **Never** claim indexing/CWV fixes without `perception_verify`.
- **Read** `agent_summary.blocking` before SEO advisory.
- Search Console and GA4 are **user-owned** — require OAuth, not API keys we host.
- **Do not** build custom crawlers — use LibreCrawl adapter.

## Provider priority

1. Google Search Console (queries, index, CWV in GSC)
2. Google Analytics 4 (traffic, landing pages)
3. LibreCrawl (technical SEO)
4. Lighthouse / PageSpeed (lab CWV + SEO score)
5. Browser Intelligence (rendering evidence via `scan_id`)
6. Bing Webmaster (optional)

## Cross-analysis playbooks

| Symptom | Check |
|---------|-------|
| Pages not indexed | GSC coverage + LibreCrawl canonicals/robots + Browser render |
| CTR dropping | GSC queries + GA4 landing pages + Lighthouse speed |
| Poor CWV | Lighthouse + Browser layout/hydration errors |
| JS-heavy site issues | Browser console + LibreCrawl JS render diff |

## Verification

After every fix:

```text
perception_observe → read blocking → perception_verify
```

Re-run `perception_seo_audit` to compare graph evidence.

## Phase note

Current phase: **architecture_v1** — provider adapters are research stubs. `perception_seo_status` reports readiness; `perception_seo_audit` returns connection map + degraded notes until Phase 1.
