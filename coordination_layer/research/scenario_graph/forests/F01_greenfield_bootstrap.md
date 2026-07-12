# Forest F01 — Greenfield Bootstrap

**Root:** `M0 empty` → `M1 bootstrapped` → `M2 scaffolded (first observable page)`
**Lifecycle stages:** S01 → S02 → S04
**Target leaves:** ~14
**Archetype coverage:** landing, marketing, portfolio, blog, saas (subset). Origin fixed to `greenfield`.

## Root decision points

1. **Intent breadth** — single-page landing, multi-page marketing, or full app skeleton?
2. **Stack choice** — framework picked by user vs to-be-inferred vs to-be-recommended.
3. **Design source at bootstrap** — none / inspiration only / Figma already exists.
4. **Dev server** — bootstrap plan yields a running dev server or not.

## Notable branches

- Intent unclear at S01 → refinement loop → S02 discovery (no code).
- Stack chosen, npm install fails → `global.tooling_broken`.
- Dev server up but blank page → S07 verify with empty-page recovery.
- Framework detection ambiguous (Vite vs Next) → S02 with `codebase: partial`.
- Bootstrap complete, no design source, no design system → hand-off to F02.

## Pruning notes

- Skip variants where "user has never seen a browser" — assumes agent operator can install Node.
- Merge `Vite+React` vs `Vite+Vue` when only stack name differs; keep only distinct behavior branches.

## Cross-links out

- F02 (design decisions)
- F04 (feature implementation on trivial single-page)
- F12 (any tooling break during bootstrap)
