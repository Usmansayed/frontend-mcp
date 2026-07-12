# Planning Pattern — Discover → Collect → Cleanup (Inspiration / Resource)

Ephemeral-blob-session discipline.

## Signature

- **Applies to states in:** cluster.design.reference_gathering, cluster.feature.resource_gap.
- **Preconditions:** query.

## Steps

1. **discover / search** — provider search returns candidates.
2. **preview / collect** — optional; opens ephemeral blob session (`insp_*` or `res_*`).
3. **decide** — user picks or dismisses.
4. **cleanup** — always call `*_session_end` before leaving the state.

## Recovery rules

- Provider offline → degraded[], continue with partial or wait.
- Session left open at episode close → forced cleanup during `session_end` at MCP level.

## States that embed this pattern

- landing.S03.design.inspiration_collected → direction_agreed_with_references → (optional) reference_registry_captured_scaffold
- landing.S06.resource_gap.icon_missing → icon_provisioned

## Coordination implications

- Cleanup is non-negotiable — the planner should schedule a session_end action at every exit edge.
- Observe-bridge (resource + scan_id) is preferred when the family match is needed; direct search otherwise.
