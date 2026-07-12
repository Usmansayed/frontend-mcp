# Forest F05 — Debugging

**Root:** S07 (verification detected an issue) or S02 (external bug report)
**Target leaves:** ~18
**Archetype coverage:** all.

## Root decision points

1. **Signal source** — console error, failed network request, visual regression, functional deviation, user report.
2. **Reproducibility** — reproducible in dev vs prod only vs intermittent.
3. **Blocking vs advisory** — from `agent_summary.blocking` or advisories.
4. **Correlation surface** — pure UI vs UI+code vs UI+config vs infrastructure.

## Notable branches

- Console error → correlate to code via `code_context` → hypothesis → fix → verify.
- Network 4xx/5xx → is it endpoint down (backend), CORS, or wrong URL?
- Visual bug → snapshot vs previous snapshot via `perception_diff`.
- Functional deviation → probe form or guards → rework → re-verify.
- Intermittent bug → cannot verify fix → capture more scans, mark state `state_confidence: low`.
- Debug session escalates to needing framework upgrade → hand off to F11.

## Pruning notes

- Same fix twice on same page not enumerated separately; verify-loop retry limits handled at planning-pattern layer.
- Console error subclasses (uncaught, unhandled promise) merged unless recovery differs.

## Cross-links out

- F04 (fix requires implementation)
- F11 (fix requires framework/library change)
- F09 (post-fix regression baseline)
- F12 (verify loop exhausted)
