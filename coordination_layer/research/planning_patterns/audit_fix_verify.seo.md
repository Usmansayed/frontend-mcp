# Planning Pattern — Audit → Fix → Verify (SEO / AI Visibility)

Iterative growth pattern for SEO and AI visibility campaigns.

## Signature

- **Applies to states in:** cluster.seo.audit_cycle.
- **Preconditions:** page indexable (S07+); website_url resolvable; optional scan_id and repo_root.

## Steps

1. **seo_status** — confirm readiness and auth mode.
2. **seo_audit** (development or professional) — produces `reasoning_context_v2`, `recommendations[]`, and (default) `ai_readiness` block.
3. **triage recs** — order by evidence weight; ignore low-value.
4. **implement fix** (S05 loop) — apply code change.
5. **seo_verify** — check the specific issue resolved.
6. **seo_query audit.diff** — confirm no other regressions.
7. Repeat 3–6.

## Recovery rules

- Pro-mode without auth → global.Sxx.env_misconfigured → seo_connect → retry.
- LibreCrawl or GSC down → global.Sxx.upstream_degraded; continue with cached graph.
- Verify shows fix present but recommendation still open → data staleness; re-audit.

## States that embed this pattern

- landing.S08.seo_campaign.audit_needed → audit_completed_dev → fix_applying → re_audit_after_fix
- marketing.S08.seo_campaign.audit_needed → audit_completed_pro → fix_applying → re_audit_after_fix
- blog.S08.seo_campaign.content_gap → content_gap_verified

## Coordination implications

- Persistent SEO graph enables `audit.diff` — planner should prefer diff over full audit when incremental.
- ai_visibility analyzers are conditionally on; treat the block presence as a state distinction (`ai_readiness_reviewed` vs `ai_visibility_disabled`).
