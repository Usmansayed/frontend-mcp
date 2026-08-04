# AI Visibility Analyzer Sources

Every analyzer in this module must be evidence-driven and grounded in publicly
documented best practices. This file is the authoritative registry — the
runtime analyzer registry in
[`registry.py`](../analyzers/registry.py) is required to match it.

**Hard rules**

- Every analyzer consumes existing `SeoEvidenceRef` items collected by the SEO
  providers (GSC, LibreCrawl, Lighthouse, Browser). Nothing here calls
  external APIs.
- If required upstream evidence is absent, the analyzer returns status
  `skipped` with a `degraded` note
  `ai_readiness_insufficient_evidence:{analyzer_id}`. Never invent metrics.
- `llms.txt` is treated as an informational signal only. It is never
  promoted as a ranking recommendation because Google's official guidance
  explicitly rejects that framing.
- No analyzer produces a recommendation for AI-only schema types,
  artificial "chunking", or third-party GEO tactics.

## Grounding

Primary source
: [Google Search Central — Optimizing for generative AI features](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide).
  Every analyzer maps to guidance in this document. Google's stance is that
  AI Overviews / AI Mode reuse the standard index; the same technical SEO
  requirements apply.

Supporting sources

- [Google — Introduction to structured data](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
- [Google — JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google — robots.txt introduction](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Google — Manage sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- [Google — Meta descriptions and titles](https://developers.google.com/search/docs/appearance/snippet)
- [Google — Understanding E-E-A-T](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Schema.org vocabulary](https://schema.org)
- [WCAG 2.1 — Section headings (2.4.10)](https://www.w3.org/WAI/WCAG21/Understanding/section-headings.html)
- [MDN — HTML semantic elements](https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Advanced_text_formatting)

Independent research is treated as **methodology reference only**, not as a
runtime dependency (e.g. Elmo's AI citation study informs how we phrase
recommendations but the engine never calls Elmo).

## Analyzer registry

| Analyzer id | Input evidence kinds | Emits `SeoEvidenceRef` when | Source / rationale |
|-------------|---------------------|-----------------------------|--------------------|
| `ai_crawlability` | `index_status`, `crawl_issue`, `technical_issue` with robots / sitemap / 404 signals | Homepage not indexed, or robots/sitemap crawl issues present | Google AI guide: "To be eligible ... a page must be indexed and eligible to be shown in Google Search with a snippet". |
| `ai_crawler_access` | `crawl_issue` metadata that mentions `robots.txt` bot rules (only if LibreCrawl surfaces them) | GPTBot / ClaudeBot / PerplexityBot explicitly disallowed **and observed in evidence** | Google robots.txt guide; opt-out is a site owner choice — analyzer reports the fact and never scolds. |
| `ai_extractability` | `rendering_issue`, `technical_issue`, `core_web_vital` | Hydration/console errors, blocking JS, LCP/CLS/INP outside "good" thresholds | Google JS SEO basics; Core Web Vitals: page must render for AI features to read content. |
| `ai_citation_readiness` | `index_status`, `crawl_issue`/`technical_issue` mentioning canonical, meta description, Open Graph, Twitter Cards | Missing canonical, meta description, OG image / description, or Twitter card | Google snippet guide + Schema.org (canonicalization; snippet eligibility governs AI citation eligibility). |
| `ai_entity_coverage` | `schema` kind, `crawl_issue` mentioning structured data | No JSON-LD detected, or missing Organization / WebSite / primary content type | Google structured data intro (entity clarity). Explicitly not an "AI schema type" — standard vocabulary only. |
| `ai_schema_quality` | Same as `ai_entity_coverage` + parse-error metadata | JSON-LD present but invalid (parse error, missing required fields per Google rich-result docs) | Schema.org validation + Google rich results guide. |
| `ai_semantic_html` | `rendering_issue` metadata, Lighthouse `technical_issue` (heading-order, hierarchical-headings, html-has-lang, heading-order) | Missing / multiple H1, heading skips, missing `lang` attribute | WCAG 2.4.10 + MDN semantic HTML. Improves both accessibility and machine extraction. |
| `ai_faq_answer_blocks` | `crawl_issue`, browser metadata surfacing visible Q&A patterns (only if provider emits it) | Site advertises "questions" content but has no heading-based Q&A blocks | Google: "prefer visible answers over markup hacks"; FAQ rich results deprecated (May 2026). |
| `ai_trust_signals` | `schema` (Organization / Author / sameAs), `index_status` metadata, browser evidence | Commercial site with no Organization schema, no author byline evidence, no `sameAs` links | Google E-E-A-T guidance: objective identity signals only, no subjective judgments. |
| `ai_internal_linking` | `internal_link`, `crawl_issue` mentioning orphan / broken internal links | Single-page or near-orphan structure detected in crawl | Google linking guide: internal links help discovery and retrieval. |
| `ai_content_structure` | `rendering_issue` / `technical_issue` on H2/H3/list density | Wall-of-text pages with no section headings or lists | Google: reward clear structure; **not** the same as artificial chunking. |
| `ai_llms_txt_optional` | Any evidence that a `/llms.txt` file was fetched (currently only if a provider explicitly emits it) | Only informational — attaches a `note` describing whether the file is present | Google explicitly says llms.txt is not needed. We record presence for observability only. |

## Contract

Each analyzer implements the following function shape (see
[`registry.py`](../analyzers/registry.py)):

```python
def analyze(evidence: list[SeoEvidenceRef], *, base_url: str) -> AiAnalyzerResult
```

`AiAnalyzerResult` is:

```python
@dataclass
class AiAnalyzerResult:
    analyzer_id: str          # matches the id in this table
    status: str               # "pass", "fail", "warn", "skipped"
    score: float              # 0.0 .. 1.0
    source_evidence_ids: list[str]
    page_url: str             # optional — empty for site-scope
    rationale: str            # human-readable, cites Google guidance
    rationale_url: str        # canonical source URL
    metadata: dict[str, Any]  # analyzer-specific metrics
```

## Scoring

- Overall AI readiness score is the mean of analyzer scores that ran
  (skipped analyzers do not lower the score). This is transparent, easy to
  audit, and matches the SEO service's existing evidence-first philosophy.
- Analyzers do **not** produce recommendations directly. They emit derived
  evidence; the recommendation engine correlates and drafts guidance via
  the existing pipeline.

## Non-goals

- Monitoring ChatGPT / Claude / Perplexity / Gemini responses.
- Recommending `llms.txt` creation.
- Recommending AI-specific schema types (none exist in schema.org).
- "Chunking" content for retrieval augmentation.
- Any GEO tactic without a public source in this file.
