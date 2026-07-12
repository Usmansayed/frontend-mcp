# AI Visibility Intelligence — Agent Guide

AI Visibility is a **derived analysis layer** on top of SEO Intelligence. It
never collects new data. It reads the SEO evidence already gathered from
Search Console, LibreCrawl, Lighthouse, and Browser Intelligence, and emits
AI-readiness signals grounded in Google's public AI search guidance.

## What this is not

- Not a rank tracker for ChatGPT / Claude / Perplexity / Gemini.
- Not a place to invent AI-only schema types.
- Not a promoter of `llms.txt` (Google's guide explicitly says it is not
  needed).
- Not a duplicate of `SeoAuditOrchestrator`. It runs inside it.

## Agent loop

```text
1. perception_seo_audit { website_url, scan_id?, include_ai_visibility: true }
2. Read reasoning_context_v2.ai_readiness         — overall + per-dimension
3. Read recommendations where category == "ai_visibility"
4. Apply fixes in code / CMS
5. perception_observe + perception_verify         — Browser Intelligence rechecks rendering
6. perception_seo_verify                          — re-audit + compare baseline
```

`include_ai_visibility` defaults to `true`. Set it to `false` if you want
only classic SEO output.

## Reading the readiness block

```json
{
  "reasoning_context_v2": {
    "ai_readiness": {
      "schema_version": "1.0",
      "overall_score": 0.62,
      "analyzers_run": 6,
      "analyzers_skipped": ["ai_crawler_access", "ai_faq_answer_blocks", "..."],
      "dimensions": {
        "ai_crawlability":       { "status": "pass", "score": 0.95, "evidence_id": "ev:ai-visibility:..." },
        "ai_citation_readiness": { "status": "fail", "score": 0.6,  "source_evidence_ids": ["ev:lighthouse:..."] }
      },
      "sources_documented_in": "src/navigation/seo_intelligence/ai_visibility/docs/ANALYZER_SOURCES.md"
    }
  }
}
```

**Rules for reading:**

- `analyzers_skipped` is not a failure. It means the upstream evidence
  needed by that analyzer was not present. Do not raise it as a problem.
- Each dimension cites `source_evidence_ids` from the upstream providers.
  Every AI recommendation must cite these plus its own derived evidence id.
- `overall_score` is the mean of analyzers that ran (skipped ones excluded).

## Graph queries

Two dedicated queries expose AI readiness at agent level:

| Query | Purpose |
|-------|---------|
| `ai.readiness.summary` | Overall + per-dimension scores from the latest audit |
| `page.ai_readiness`    | Page-scoped AI signals + cited upstream evidence |

Call via `perception_seo_query`.

## Analyzer registry

Twelve analyzers, all evidence-driven. See
[`ANALYZER_SOURCES.md`](./ANALYZER_SOURCES.md) for the source citations that
back every analyzer.

| id | fires when |
|----|-----------|
| `ai_crawlability` | GSC index verdict FAIL, or crawl blockers on the site |
| `ai_crawler_access` | Only if robots.txt evidence explicitly mentions AI bots |
| `ai_extractability` | Rendering blockers or CWV outside "good" thresholds |
| `ai_citation_readiness` | Missing title, meta description, canonical, OG, or Twitter Card |
| `ai_entity_coverage` | No JSON-LD detected in the crawl |
| `ai_schema_quality` | Invalid JSON-LD reported by the crawl |
| `ai_semantic_html` | Multiple H1s, heading order issues, missing `lang` |
| `ai_faq_answer_blocks` | Only if providers surface Q&A signals |
| `ai_trust_signals` | Missing Organization / author / sameAs signals |
| `ai_internal_linking` | Orphan pages, broken links, or non-descriptive anchors |
| `ai_content_structure` | Wall-of-text pages with no subheadings |
| `ai_llms_txt_optional` | Informational — never a recommendation |

## Verification

AI recommendations are verified with the existing loop. `_judge_recommendation`
compares baseline vs current derived `ai_visibility` evidence: higher status
rank (`fail` -> `warn` -> `pass`) or a score improvement above 0.05 counts as
passed.

## Non-goals

- We do not fabricate AI citation rates or SERP snapshots.
- We do not scrape ChatGPT / Perplexity responses.
- We do not recommend GEO tactics without a public source in
  [`ANALYZER_SOURCES.md`](./ANALYZER_SOURCES.md).
