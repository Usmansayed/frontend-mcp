# Forest F04 — Feature Implementation

**Root:** S05 → S06 → S07
**Target leaves:** ~30 (largest forest)
**Archetype coverage:** all.

## Root decision points

1. **Feature type** — form, list/table, modal, chart, auth flow, navigation.
2. **State depth** — stateless UI vs auth-required vs multi-step flow.
3. **API integration** — none / mock / live.
4. **Verification depth** — smoke only vs full success criteria.

## Notable branches

- Form (validated): probe-form baseline → invalid submit path → valid submit path → verify each.
- Auth flow: probe guards → auth gate → state save → subsequent runs restore.
- Multi-step flow: flow describe → per-checkpoint verify.
- API failure during integration: `global.upstream_degraded` recovery.
- Component acquired via F03 but adaptation still needed: repair loop.
- Verify passes but `blocking` non-empty → re-observe → diff → adjust.

## Pruning notes

- Framework-specific idioms (React vs Vue) merged; behavior branches only.
- "Component perfect first time" collapsed into one variant.

## Cross-links out

- F05 (bug found)
- F06 (quality after ship)
- F07 (SEO after page is public)
- F08 (consistency after visual signal)
- F09 (regression baseline capture)
- F12 (auth gate, degraded)
