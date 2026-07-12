# Forest F10 — Production Maintenance

**Root:** S11 production
**Target leaves:** ~12
**Archetype coverage:** all shipped projects.

## Root decision points

1. **Trigger** — user report, alerting, drift, dependency notice, hotfix.
2. **Fix urgency** — hotfix (skip stages) vs scheduled.
3. **Persistent evidence** — SEO graph / PDG staleness.
4. **Rollback readiness** — baseline available or not.

## Notable branches

- Hotfix path: production URL scan → hypothesis → local reproduction → fix → staging verify → deploy.
- Drift accumulated → schedule PDG refresh + SEO re-audit as background.
- Dependency upgrade offered → risk assessment → migration schedule (F11).
- Monitoring surfaces regression → F09 / F05 loop.

## Pruning notes

- Recurring maintenance (weekly re-audits) modeled as one recurrence state, not many.

## Cross-links out

- F05 (debug)
- F09 (regression / release for hotfix)
- F11 (major upgrade)
- F12 (production URL unreachable)
