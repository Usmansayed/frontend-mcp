# Resolver Intelligence

Fast deterministic lookups for coding agents — replaces slow `perception_code_context` (CRG) for common tasks.

## Agent guide

MCP resource: **`perception://resolver-guide`**

Playbook: **AGENT_GUIDE §10**

## Tools

| Tool | Purpose |
|------|---------|
| `perception_resolve_route` | Route → component file |
| `perception_validate_route_claim` | Validate agent claim |
| `perception_resolve_component` | Component name → file |
| `perception_validate_component_claim` | Validate component claim |
| `perception_resolve_design_token` | Token → CSS/tailwind/DTCG |
| `perception_resolve_state_owner` | State key → store file |
| `perception_resolve_api_endpoint` | API path → handler |
| `perception_resolve_layout` | Regions from design snapshot |
| `perception_correlate_live` | DOM cross-check with `scan_id` |

## Response shape

`data.resolution.status`: `resolved` | `ambiguous` | `not_found` | `unsupported`

Follow `fallback` when not resolved — do not retry the same params.

## Performance

- SYNC_OFFLOAD, &lt;200ms target
- Always pass `repo_root`
- Call tools one at a time (no parallel MCP batches)
