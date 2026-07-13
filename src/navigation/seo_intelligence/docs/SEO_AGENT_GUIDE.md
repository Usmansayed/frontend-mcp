# SEO Intelligence — Agent Guide

Read this guide before calling `perception_seo_*` tools.

## What this module is

SEO Intelligence is an **evidence-first SEO platform** (ADR-027). Five evidence providers supply facts; everything flows through **`reasoning_context_v2`** — deterministic fallback always available; host LLM reasoning when Bedrock credentials are configured (Sprint 3). Browser Intelligence verifies results.

**Design rule:** Nothing bypasses `reasoning_context_v2`. AI never talks to providers directly.

**AI Visibility layer.** Every audit runs the AI Visibility adapter, which
derives `ai_visibility` evidence from the collected SEO evidence and attaches
an `ai_readiness` block to `reasoning_context_v2`. Filter recommendations by
`category == "ai_visibility"` for AI-readiness fixes. See
[`../ai_visibility/docs/AI_VISIBILITY_AGENT_GUIDE.md`](../ai_visibility/docs/AI_VISIBILITY_AGENT_GUIDE.md).

## Two-tier modes

### Development SEO (default)

No authentication. Active while the agent builds a website.

| Providers | Browser Intelligence, Lighthouse, LibreCrawl |
| Validates | Metadata, schema, CWV, crawl, rendering, internal links, semantic HTML |

```text
perception_seo_audit_start {
  "website_url": "https://example.com",
  "scan_id": "...",
  "repo_root": "/path/to/frontend"
}
```

Then poll with `perception_seo_audit_poll` until terminal status.

Pass `repo_root` so Sprint 2 can attach `codebase_hints` and `browser_code_links` to each page.

Set `ai_reasoning: false` to force deterministic recommendations (no Bedrock). Omit for auto (uses LLM when AWS creds available).

### Professional SEO Optimization

Only when the user explicitly asks (e.g. *optimize my SEO*, *connect Search Console*, *analyze with Google data*).

```text
perception_seo_connect { "website_url": "...", "action": "connect_google" }
perception_seo_audit { "website_url": "...", "mode": "professional" }
```

OAuth opens in the browser automatically (`interactive: true`). After connect, audits combine GSC, GA4, LibreCrawl, Lighthouse, and Browser Intelligence.

## Agent loop

```text
1. perception_seo_status          — module phase + provider connections
2. perception_seo_connect         — register website_url; OAuth only on demand
3. perception_seo_audit_start       — enqueue audit → audit_job_id (<500ms, non-blocking)
4. perception_seo_audit_poll        — poll until completed | failed | cancelled
5. perception_seo_query             — graph queries: page.issues, audit.diff, site.traffic_signals
6. Fix code / config              — read reasoning_units, codebase_hints, browser_code_links
7. perception_observe + verify    — Browser Intelligence verifies rendering/index fixes
8. perception_seo_verify          — re-audit + compare graph baseline → mark verified
```

### Async audit (required for agents)

**Do not** call `perception_seo_audit` in interactive loops — it blocks the MCP server.

```text
perception_seo_audit_start({
  "website_url": "https://example.com",
  "scan_id": "...",
  "repo_root": "/path/to/frontend"
})
→ data.audit_job_id

perception_seo_audit_poll({ "audit_job_id": "audit_job_..." })
→ data.seo_audit_job.status, partial evidence

perception_seo_audit_cancel({ "audit_job_id": "..." })   // optional
```

Legacy `perception_seo_audit` remains for scripts only; agents must use start + poll.

## Onboarding (users)

**Initial setup:** website URL only. SEO Intelligence is ready immediately.

**On-demand auth:** when the user requests Search Console / GA4 analysis, prompt *Connect your Google Search Console* and run `perception_seo_connect` with `action=connect_google`. When they request Bing analysis, prompt *Connect your Bing Webmaster account* and run `action=connect_bing`.

GSC, GA4, LibreCrawl, and Lighthouse are configured automatically. Advanced property IDs only for discovery failures.

## Hard rules

- **Never** recommend without `evidence_ids` / `evidence_used`.
- **Never** claim indexing/CWV fixes without `perception_verify`.
- **Read** `reasoning_context_v2` (schema `2.0`) and `reasoning_units` before improvising SEO advice.
- **Read** `agent_summary.blocking` before SEO advisory.
- Search Console and GA4 are **user-owned** — require OAuth.
- **Do not** build custom crawlers — use LibreCrawl.

## Evidence providers (only these)

1. Google Search Console — queries, index, coverage
2. Google Analytics 4 — traffic, landing pages
3. LibreCrawl — technical crawl
4. Lighthouse / PageSpeed — lab CWV + SEO score
5. Browser Intelligence — rendering, DOM, console, metadata (`scan_id`)

## Recommendation fields

Every recommendation includes:

- Title, root cause, evidence used, confidence, priority (impact-weighted in Sprint 2)
- Business impact, implementation steps, verification steps
- `metadata.codebase_hints` when `repo_root` was provided

## Sprint 2 intelligence fields

| Field | Use |
|-------|-----|
| `reasoning_context_v2.sprint` | `"intelligence_v2"` when enrichment ran |
| `pages[].impact` | Prioritize high-traffic / high-impression pages |
| `pages[].codebase_hints` | Likely files to edit (`file`, `reason`, `confidence`) |
| `pages[].browser_code_links` | Tie `scan_id` + rendering evidence to `likely_files` |
| `reasoning_units[]` | Sorted by `impact` then `confidence` — primary fix queue |
| `reasoning_context_v2.ai_reasoning` | `source: llm` or `deterministic_fallback`; read `validation_errors` if fallback |

## Sprint 3 — AI reasoning

When Bedrock is available, `perception_seo_audit` feeds `reasoning_units[]` to the host LLM. Every draft recommendation is post-validated:

- Must cite `evidence_ids` from the audit snapshot
- Must not invent large metrics absent from evidence
- Must map to a known `reasoning_unit_id` when provided

Failed validation → **deterministic fallback** (`build_recommendations`) — still trustworthy, marked in `ai_reasoning.degraded`.

## Cross-analysis playbooks

| Symptom | Check |
|---------|-------|
| Pages not indexed | GSC coverage + LibreCrawl canonicals/robots + Browser render |
| CTR dropping | GSC queries + GA4 landing pages + Lighthouse speed |
| Poor CWV | Lighthouse + Browser layout/hydration errors |
| JS-heavy site issues | Browser console + LibreCrawl JS render diff |
| Opportunities | High impressions/low CTR, position 8–20, weak metadata |

## Verification

After every fix:

```text
perception_observe → read blocking → perception_verify
perception_seo_verify → compare baseline → mark recommendation verified
```

## Phase note

**agent_ready_v4** — Evidence-first pipeline (ADR-027) through Sprint 3, plus graph query API, provider agreement v2, partial AI validation, golden regression fixtures. Optimized for AI coding agents — not enterprise SEO dashboards.
