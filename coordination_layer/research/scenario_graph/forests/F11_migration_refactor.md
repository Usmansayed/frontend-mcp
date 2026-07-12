# Forest F11 — Migration & Refactor

**Root:** S12 evolution
**Target leaves:** ~16
**Archetype coverage:** all mature projects (M4+).

## Root decision points

1. **Migration type** — framework major version, build tool swap, styling system swap, design-system overhaul, redesign.
2. **Coexistence period** — big-bang vs incremental.
3. **Prior evidence** — baselines available for comparison.
4. **Consumer impact** — API breakage risk (esp. component_library).

## Notable branches

- Framework major bump: detect current → detect target → docs fetch (framework_docs) → migration plan → incremental page verify loop.
- Redesign: capture "before" snapshots → new design in F02/F03 → per-page swap → diff vs baseline.
- Design system overhaul: PDG standards updated → per-page consistency audit → propose fixes en masse.
- Component library breaking change: bump semver plan → downstream consumer notification.

## Pruning notes

- Per-page migration modeled as one recurring pattern state.
- Vendor-specific migration guides not enumerated; behavior branches only.

## Cross-links out

- F04 (implement migration changes)
- F09 (large regression suite after migration)
- F08 (consistency after redesign)
- F12 (migration fails / rollback)
