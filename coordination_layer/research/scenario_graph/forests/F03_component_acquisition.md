# Forest F03 — Component Acquisition

**Root:** component_replacement | inspiration-driven new component
**Target leaves:** ~18
**Archetype coverage:** any UI project.

## Root decision points

1. **Query clarity** — well-formed vs vague; do we need `perception_plan_component_search`?
2. **Foundation availability** — search returns 0 / few / many candidates.
3. **Integration mode** — dry-run report only vs live install (roadmap gap, `mcp_ready: false`).
4. **Repair needed** — does the selected component match project conventions?

## Notable branches

- Search plan generated → search executed → candidates ranked → select foundation.
- 0 candidates for query → refine plan → re-search → eventually fallback (F02 inspiration-driven).
- Live install requested → `mcp_ready: false` state cluster; still describe expected outcome.
- Dry-run integration reports needed_repairs → planning state → back to select or accept.
- User rejects top candidate → cycle to next foundation.

## Pruning notes

- Provider-specific branches (shadcn vs external) merged unless behavior differs.
- Failure to reach external registry treated as `global.upstream_degraded`.

## Cross-links out

- F04 (implement feature around selected component)
- F08 (design-review the integrated component)
- F02 (fall back to inspiration when no component fits)
- F12 (registry offline)
