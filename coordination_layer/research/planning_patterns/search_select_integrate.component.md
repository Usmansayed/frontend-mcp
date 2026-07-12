# Planning Pattern — Search → Select → Integrate (Component)

Component acquisition sequence.

## Signature

- **Applies to states in:** cluster.component.acquisition_pipeline.
- **Preconditions:** repo_root; user need for a component.

## Steps

1. **plan_component_search** — if query is vague, produce SearchPlan.
2. **search_components** — provider search.
3. **select_component_foundation** — combines Framework + Codebase + Design Sense + Consistency + Browser contracts to score candidates.
4. **integrate_component** — dry-run by default; live install is scaffold.
5. **repair loop** — apply needed_repairs; re-verify.

## Recovery rules

- Zero candidates → refine plan or fallback to inspiration (`inspiration_fallback`).
- Provider offline → `provider_offline` state → wait or use local.
- License unresolved → `license_check_pending` → resolve before integrate.

## States that embed this pattern

- complib.S05.component_replacement.query_vague → plan_ready → candidates_ranked → candidate_selected → integration_dry_run_report → integrated_and_verified

## Coordination implications

- Live install path is `mcp_ready: false` — coordination must avoid selecting it today.
- Selection cross-consults five contracts in parallel; the planner should not serialize them.
