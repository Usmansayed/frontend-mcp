# Scenario Taxonomy — 12 Forests

The state space is enumerated by walking twelve **scenario forests**. Each forest is rooted at a lifecycle stage (or a cross-cutting failure surface) and recursively branches on decisions a real project encounters. Leaves are stable states; edges between forests exist and are captured via `possible_next_states` in state YAMLs.

Forests are the **search seed**, not the final taxonomy. Clustering in Phase 4 will regroup states across forests by fingerprint.

Per-forest documents live under `forests/*.md`. Each per-forest doc lists the root decision points, notable branches, and pruning rationale.

---

## Forest inventory

| # | Forest ID | Root stage | Target leaves | Purpose |
|---|-----------|-----------|---------------|---------|
| F01 | greenfield_bootstrap | S01→S02→S04 | 14 | empty → dev-server-up → first observable page |
| F02 | design_led_build | S03 | 20 | Figma/inspiration/design-system permutations before code |
| F03 | component_acquisition | S05 | 18 | search → select → integrate (dry-run vs live gap) |
| F04 | feature_implementation | S05→S07 | 30 | forms, dashboards, auth flows, verification loop |
| F05 | debugging | S07↔S02 | 18 | console/network/visual/functional bug classes |
| F06 | quality_campaigns | S08 | 18 | a11y, perf, lighthouse-SEO paths |
| F07 | seo_and_ai_visibility | S08 | 16 | dev vs pro mode, audit → fix → verify → derive AI |
| F08 | design_review_consistency | S09 | 16 | snapshot → sense → PDG audit → propose fix |
| F09 | release_regression | S10 | 14 | regression baselines, staging verify |
| F10 | production_maintenance | S11 | 12 | hotfix, drift, dependency upgrade |
| F11 | migration_refactor | S12 | 16 | framework migration, redesign, deprecation |
| F12 | global_failure_recovery | any | 10 | auth gate, upstream degraded, verify exhaustion |

Total target: 192 stable states (within the plan's 150–250 window).

---

## Forest recursion rule

Each forest recurses on **three decision axes**, in this order (avoids state explosion):

1. **Evidence availability** — is the required evidence `known` / `verified`? If not, insert a discovery/observation state.
2. **Module gating** — does the situation need a module that requires a run-gate (auth, PAT, dev server)? If gated but not satisfied, branch to a global gate state.
3. **Success vs failure** — every action edge has at least one failure state and at least one recovery path.

We stop recursing when:

- All exits point to previously-defined states, or
- All next states are `global.*` failure states, or
- The variant would only differ by a permutation already covered.

---

## Forest cross-links

Every forest may exit into another. The following cross-links are guaranteed:

- F01 → F02 (bootstrap → design decisions)
- F01 → F04 (bootstrap → straight to feature build if design is trivial)
- F02 → F03 (design decided → component search)
- F03 → F04 (component ready → implement feature around it)
- F04 → F05 (bug found during implementation → debugging)
- F04 → F07 (feature complete on public page → SEO campaign)
- F05 → F08 (visual bug → consistency review needed)
- F06 → F04 (quality finding → back to implementation for fix)
- F07 → F04 (SEO recommendation involves code change → implementation)
- F08 → F03 (consistency violation → replace component)
- F09 → F05 (regression detected → debugging)
- F09 → F10 (staging clean → production)
- F10 → F11 (drift accumulated → migration)
- F11 → F04 (migration lands → feature reimplementation)
- F12 → any (recovery from global failure re-enters original forest)

These cross-links become the primary source of "recurring transitions" in the Phase 5 coordination input.

---

## Ordering of enumeration (Phase 3)

Batches are grouped so the state graph builds bottom-up:

- **Batch 1 (forests F01–F06):** foundational states — bootstrap, design, components, implementation, debugging, quality. Producing these first establishes the "spine" that later forests hang off.
- **Batch 2 (forests F07–F12):** growth, consistency, release, maintenance, migration, and global recovery — all richer with cross-links.

Cross-links from Batch 2 to Batch 1 states are inserted as we discover them; we do not backfill Batch 1 states purely to satisfy Batch 2 links, we instead identify the missing states and add them explicitly.
