# Frontend Lifecycle Ontology

This document defines the **vocabulary** that every state in the corpus uses. It is deliberately independent of MCP tool names — the ontology is what a senior frontend engineer would recognize whether or not any tooling exists.

Every state YAML tags itself on five orthogonal axes. Together, these tags let clustering and coordination reason about states without reading their prose.

---

## Axis A — Project maturity (7 levels)

Maturity is a monotonic property: projects move forward, and only occasionally regress. It captures the state of the codebase and its shipped surface — not the state of any single feature.

| Level | Name | Definition | Typical evidence |
|-------|------|------------|------------------|
| M0 | `empty` | No repo, or repo has only README and license. No package manager, no framework, no routes. | No `package.json`, no dev server. |
| M1 | `bootstrapped` | Framework and stack chosen; dev server can start; one boilerplate page renders. | `package.json`, framework detected, first `perception_health` succeeds. |
| M2 | `scaffolded` | First real pages/routes exist. Design decisions may still be pending. | Multiple routes discoverable via `code_context`; observable UI. |
| M3 | `feature_development` | Active build-out of features, forms, flows. Bugs expected. | Frequent scans, verify loops, iteration. |
| M4 | `pre_release` | Feature-complete for a milestone. Quality/regression/SEO passes begin. | Audit reports, regression baselines, blocking empty on primary flows. |
| M5 | `production` | Deployed. Live users. Changes are focused and risk-managed. | External URL reachable; monitoring signals; historic SEO graph. |
| M6 | `legacy_maintenance` | Owned but not evolving. Bug fixes, dependency upgrades, deprecations. | Framework version behind current, sparse code churn, drift alerts. |

**Regression is possible** (e.g., `production` project undergoing framework migration can slip into `pre_release`). States carry maturity as a tag; transitions may move backward on the maturity axis.

---

## Axis B — Lifecycle stage (12 stages)

Where in the *current unit of work* the project sits. Unlike maturity, stage is per-episode and cyclic.

| Stage | Meaning | Typical entry | Typical exit |
|-------|---------|---------------|--------------|
| `S01_intent` | Goal being formed. What are we trying to do? | User says "add X" / "fix Y" / "make it fast" | Goal is describable in one sentence. |
| `S02_discovery` | Facts collection: stack, existing UI, references. | Fresh session, new episode. | Enough evidence to plan design or code. |
| `S03_design` | Visual/UX decisions: Figma, inspiration, tokens. | Discovery complete, no design yet. | Design brief or reference set. |
| `S04_architecture` | Route layout, data flow, component boundaries. | Design decided (or not needed). | Component tree agreed. |
| `S05_implementation` | Coding. | Architecture set. | Code exists on branch. |
| `S06_integration` | APIs, third-party libs, assets, tokens plumbed through. | Implementation touches external surfaces. | Integrations pass smoke checks. |
| `S07_verification` | Functional + visual correctness. | Code + integrations exist. | Verified against success criteria. |
| `S08_quality` | A11y, performance, SEO, AI visibility. | Verification passes on happy paths. | Quality thresholds met (project-defined). |
| `S09_consistency` | Design system alignment, token drift audits. | Feature is functionally complete. | PDG audit clean or accepted deviations. |
| `S10_release` | Staging deploy, regression, sign-off. | Quality + consistency complete. | Approved for production. |
| `S11_production` | Live monitoring, incident response. | Release complete. | Next episode or hotfix. |
| `S12_evolution` | Migration, redesign, deprecation. | Long-term shift signaled. | New milestone opened at earlier stage. |

Stages are **cyclic**: a debug episode may go S07 → S03 → S05 → S07 within a single day. Stages are also **skippable**: a landing-page redesign may skip S06.

---

## Axis C — Evidence posture

Per-domain, per-state tag. Domains are chosen to match how the MCP produces evidence, not for taxonomic elegance.

**Domains:**

- `ui_runtime` — what the live page shows (DOM, screenshot, network).
- `codebase` — files, routes, framework config, tokens on disk.
- `design_source` — Figma, mockups, inspiration references.
- `design_system` — tokens, components, standards captured in PDG.
- `seo` — SEO graph, `reasoning_context_v2`, indexability signals.
- `quality` — accessibility, performance, best-practices audits.
- `assets` — icons, fonts, illustrations required by the feature.

**Postures per domain:**

| Posture | Meaning |
|---------|---------|
| `unknown` | No evidence gathered, no cached graph, agent must not assume anything. |
| `partial` | Some evidence exists but is not fresh, complete, or high-fidelity. |
| `known` | Recent, high-fidelity evidence available. Agent may reason over it. |
| `verified` | Evidence has been used to verify a success criterion. |
| `regressed` | Previously `verified` domain now shows blocking issues. |

**Rules:**

- Postures are **monotonic within an episode** except via explicit re-observation or a regression event.
- A state's `verification_requirements` typically require certain domains to be `verified`.
- `regressed` is a signal for coordination to schedule remediation rather than progression.

---

## Axis D — Project archetype (24 types, see `project_archetypes.yaml`)

Archetype captures durable structural properties of the project. Two archetypes for the same site are possible (e.g., `saas_dashboard` + `monorepo`).

Categories:

- **Site class** (10): `landing`, `marketing`, `portfolio`, `blog`, `docs`, `ecommerce`, `saas_dashboard`, `admin_panel`, `design_system`, `component_library`.
- **Structure** (5): `monorepo`, `single_app`, `hybrid`, `micro_frontend`, `island_architecture`.
- **Rendering posture** (4): `csr`, `ssr`, `ssg`, `pwa`.
- **Origin** (5): `greenfield`, `existing_mature`, `legacy`, `fork`, `enterprise_constrained`.

Two dimensions typically dominate a state's behavior:

- **Site class** shapes which quality domains are non-negotiable (e.g., `ecommerce` demands SEO + performance verification; `admin_panel` demands a11y + form correctness).
- **Origin** shapes evidence posture at the start (a `legacy` project rarely has `design_system: known`; a `greenfield` project has `codebase: unknown` at M0).

---

## Axis E — Situation class

The reason this episode exists. Situations are the "trigger" side of the state space.

| Class | Trigger | Typical starting stage |
|-------|---------|------------------------|
| `new_feature` | User wants a capability that doesn't exist. | S01 |
| `ui_bug` | Visual defect on a rendered page. | S07/S02 |
| `functional_bug` | Behavior does not match spec (form, API, flow). | S07/S02 |
| `regression` | Previously working behavior broken. | S07 |
| `redesign` | Whole page/section restyle. | S03 |
| `framework_migration` | Move stack (React 18 → 19, Next 13 → 15, etc.). | S12 |
| `component_replacement` | Swap out a component. | S05 |
| `accessibility_remediation` | Fix a11y findings. | S08 |
| `performance_remediation` | Fix perf findings. | S08 |
| `seo_campaign` | Improve organic reach. | S08 |
| `ai_visibility_campaign` | Improve AI-search readiness. | S08 |
| `consistency_cleanup` | Fix token/spacing/color drift. | S09 |
| `hotfix` | Urgent production fix. | S11→S05 loop |
| `resource_gap` | Missing icon/font/image. | S06 |
| `inspiration_needed` | No design direction yet. | S03 |
| `auth_blocked` | Guarded route needs a human. | any stage |
| `degraded_upstream` | External dependency (Figma, Lighthouse, Grounded Docs) unavailable. | any stage |
| `documentation` | Need to explain something (README, ADR). | S11/S12 |
| `dependency_upgrade` | Package/lockfile update. | S12 |
| `code_review` | Assessing a PR / branch. | S10 |
| `release_prep` | Staging → prod. | S10 |
| `regression_baseline` | Capture a known-good baseline. | S07/S10 |

---

## Naming discipline

- **State ID**: `{archetype_abbrev}.{stage}.{situation}.{variant}` (see `research/reports/03_state_space_methodology.md` when written).
- **Actions**: verbs in snake_case, semantic ("`derive_ai_visibility`", not "`perception_seo_audit`").
- **Modules referenced in state YAML**: canonical module names from the inventory (`visual_browser`, `seo_intelligence`, etc.).
- **Cross-cutting states**: prefixed `global.*` — apply across archetypes.

---

## How a state uses these axes

Each state fixes a value for each axis (or `null` when N/A). Clustering in Phase 4 groups states whose 5-axis fingerprint is identical or near-identical, producing meta-states.

Example fingerprint:

```yaml
project_archetype: saas_dashboard
project_maturity: feature_development
lifecycle_stage: S05_implementation
situation_class: new_feature
evidence_posture:
  ui_runtime: partial
  codebase: partial
  design_source: unknown
  design_system: partial
  seo: unknown
  quality: unknown
  assets: unknown
```

Two states with the same fingerprint but different transitions are still separate states — the fingerprint enables clustering, not deduplication.
