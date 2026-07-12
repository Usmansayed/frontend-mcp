# Forest F06 — Quality Campaigns

**Root:** S08 quality
**Target leaves:** ~18
**Archetype coverage:** all.

## Root decision points

1. **Domain** — a11y, performance, best-practices, Lighthouse-SEO (distinct from SEO Intelligence).
2. **Trigger** — pre-release checklist vs targeted remediation vs continuous.
3. **Toolchain availability** — Lighthouse present vs missing (`degraded`).
4. **Scope** — single page vs site-wide.

## Notable branches

- A11y audit → findings → remediation → re-audit → verified.
- Perf audit → LH scores below budget → identify offenders (network, largest contentful paint) → fix → re-audit.
- LH-SEO vs SEO Intelligence: both may run; results reconciled at S10.
- Lighthouse missing → skip audit, mark `quality: partial` with `degraded[]` note.
- Full-diagnosis triggered proactively at end of milestone.

## Pruning notes

- Individual LH scores per page merged into "some pages below budget" vs "all above budget".
- Site-wide iteration modeled as a loop over per-page states.

## Cross-links out

- F04 (remediation requires implementation)
- F07 (SEO remediation)
- F09 (release checklist)
- F12 (Lighthouse down)
