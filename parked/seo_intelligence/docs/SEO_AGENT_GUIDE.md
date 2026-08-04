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

Runs **instantly inline** (2–5s usefulness-first budget). No authentication, no crawl, no Search Console, no background job.

| Providers | Browser Intelligence + AI Visibility (derived) |
| Validates | Metadata, semantics, headings, schema hints, internal links, a11y, lightweight technical heuristics |

**Requires `scan_id`** from `perception_observe` or `perception_navigate_and_observe` first.

```text
perception_navigate_and_observe({ "session_id": "...", "url": "...", "detail": "summary_only" })
→ scan_id

perception_seo_audit_start({
  "website_url": "https://example.com",
  "scan_id": "...",
  "repo_root": "/path/to/frontend"
})
→ data.status = "completed", data.instant = true — no polling
```

**Localhost** (`localhost`, `127.0.0.1`) auto-detects development mode even without an explicit `mode`.

Pass `repo_root` so Sprint 2 can attach `codebase_hints` and `browser_code_links` to each page.

Set `ai_reasoning: false` to force deterministic recommendations (no Bedrock). Omit for auto (uses LLM when AWS creds available).

### Professional SEO Optimization

Only when the user explicitly asks (e.g. *full SEO audit*, *connect Search Console*, *analyze with Google data*).

Runs **asynchronously** — poll until terminal.

| Providers | GSC, GA4, LibreCrawl, Lighthouse, Browser Intelligence, historical evidence |
| Flow | `seo_audit_start` → background collection → progress → partial results → final report |

```text
perception_seo_connect { "website_url": "...", "action": "connect_google" }
perception_seo_audit_start { "website_url": "...", "mode": "professional" }
→ data.audit_job_id

perception_seo_audit_poll({ "audit_job_id": "audit_job_..." })
```

OAuth opens in the browser automatically (`interactive: true`). After connect, audits combine GSC, GA4, LibreCrawl, Lighthouse, and Browser Intelligence.

## Agent loop

```text
1. perception_seo_status          — module phase + provider connections
2. perception_seo_connect         — register website_url; OAuth only on demand
3. perception_observe             — scan page → scan_id (use detail=summary_only for speed)
4. perception_seo_audit_start     — development: instant result; professional: audit_job_id
5. perception_seo_audit_poll      — professional only — poll until completed | failed | cancelled
6. perception_seo_query           — graph queries: page.issues, audit.diff, site.traffic_signals
7. Fix code / config              — read reasoning_units, codebase_hints, browser_code_links
8. perception_observe + verify    — Browser Intelligence verifies rendering/index fixes
9. perception_seo_verify          — re-audit + compare graph baseline → mark verified
```

### Development vs professional audit

**Development (default):** synchronous, returns `data.status: completed` with `data.instant: true`.

**Professional:** returns `data.audit_job_id` — poll `perception_seo_audit_poll` for progress and partial evidence.

```text
perception_seo_audit_poll({ "audit_job_id": "audit_job_..." })
→ data.seo_audit_job.status, partial evidence

perception_seo_audit_cancel({ "audit_job_id": "..." })   // optional
```

Legacy `perception_seo_audit` remains for scripts only; agents should use `perception_seo_audit_start`.

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

When Bedrock is available, `perception_seo_audit_start` (development or completed professional audit) feeds `reasoning_units[]` to the host LLM. Every draft recommendation is post-validated:

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
