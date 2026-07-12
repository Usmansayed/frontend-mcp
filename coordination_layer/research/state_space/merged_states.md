# Merged States — Equivalence Notes

This document records **merges and near-duplicates** we identified during enumeration and Phase 4 review. Nothing is deleted — merges are annotated with `parent_cluster` on the leaf YAMLs (see `abstracted/cluster_index.md`) and a note here.

## Type 1 — Explicit near-duplicates

None. Each of the 150 leaves has a distinct combination of `(state_id, entry_conditions, exit_conditions)`. Where duplicates would have arisen, we consolidated at enumeration time (see the exploration log's "Discarded" sections).

## Type 2 — Frameworks and providers merged as tags

- **Framework identity** (React/Vue/Svelte/Angular) is a tag on `codebase_intelligence` output, not a state distinction. All bootstrap variants converge into a single `stack_chosen` state.
- **Component providers** (shadcn ecosystem vs external registries) are candidates ranked in `candidates_ranked`, not separate states.
- **SEO recommendation type** (meta title, canonical, schema, indexability) is a tag on the audit findings, not a state.
- **A11y rule category** is a tag on Lighthouse findings, not a state distinction.
- **Design system rule category** (spacing vs color vs typography) is a tag on consistency deviations.

## Type 3 — Cross-forest structural similarity (kept separate on purpose)

- `dssite.S05.consistency_cleanup.applying_fix` vs `marketing.S05.redesign.applying_fix` have the same fingerprint but different source of finding (Consistency vs Design Sense). Kept separate because their `relevant_modules` and re-verification predicates differ.
- `marketing.S07.new_feature.change_scope_ready` and `marketing.S07.new_feature.navigation_change.verified` share stage/situation but different scope of change; kept separate for coordination granularity.
- Multiple archetype variants of "SEO audit needed" (landing vs marketing vs ecom vs blog) are kept separate because dominant quality domains and verification requirements differ per archetype.

## Type 4 — Global states factored out

Instead of duplicating error handling per forest, we produced 12 `global.*` states that non-terminal states reference in `failure_states`. Every recovery path is expressed once.

## Type 5 — Aspirational states (kept, tagged `mcp_ready: false`)

Three:

- `landing.S03.design.reference_registry_captured_scaffold` — Design Reference Registry has no MCP surface.
- `complib.S05.component_replacement.integration_live_scaffold` — live install/repair is scaffold.
- `marketing.S09.consistency_cleanup.token_import_pending_scaffold` — Design Workflow token import is roadmap.

Each cites its gap in `mcp_ready_gap` referring to `reports/01_mcp_module_inventory.md`.

## Type 6 — Terminal collapse

The canonical terminal state `global.Sxx.verify_success_terminal` unifies all successful episode closures. Individual "clean" states (`marketing.S08.a11y_remediation.clean`, `blog.S08.seo_campaign.content_gap_verified`, etc.) point onward rather than being terminal themselves — the episode ends only when the whole task is closed.

## Discarded candidates not represented in any state

Listed for future readers considering re-adding:

- **"npm install fails halfway"** — merged into `global.Sxx.tooling_broken`.
- **"individual Lighthouse metric below budget"** — represented as tags on `perf_remediation.findings_open`.
- **"design mockup approved verbally"** — merged into `direction_agreed_no_references`.
- **"user forgot to provide PAT after being asked"** — folded into `global.Sxx.user_abandoned`.
- **"MCP bug"** — out of scope for the project state space.
- **"per-page a11y iteration"** — modeled as loop over `findings_open` rather than N distinct states.
