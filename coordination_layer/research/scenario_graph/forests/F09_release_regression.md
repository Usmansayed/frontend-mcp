# Forest F09 — Release & Regression

**Root:** S10 release
**Target leaves:** ~14
**Archetype coverage:** all shipped projects.

## Root decision points

1. **Baseline availability** — regression baseline captured vs missing.
2. **Staging vs production** — target environment.
3. **Scope** — single page vs multi-page smoke vs full regression suite.
4. **Sign-off** — verified quality budget vs deviations accepted.

## Notable branches

- Capture baseline → snapshots + scans committed → future diffs meaningful.
- Regression detected → `regressed` posture → hand off to F05.
- Staging fresh env → session_start needs new URL → re-verify.
- Sign-off decision requires human → global `auth_gate`-like wait.

## Pruning notes

- Per-page regression iterations merged into "some pages regressed" vs "clean".
- Time-based staleness of baseline modeled as posture transition, not new state.

## Cross-links out

- F05 (regression → debug)
- F10 (release complete → production)
- F06/F07 (last-mile quality/SEO pass)
- F12 (staging env down)
