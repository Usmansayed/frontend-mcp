# Flows subsystem

**Status:** ✅ shipped

**Modules:** `mcp/handlers.py` (`perception_flow_describe`), guard/form probes

## Tools

| Tool | Purpose |
|------|---------|
| `perception_flow_describe` | Describe multi-step UI flow with checkpoints |
| `perception_probe_form` | Form validation behavior |
| `perception_probe_guards` | Route guard / auth redirect suite |

## Flow model

Agent describes intended flow; server returns structured checkpoint graph. Agent verifies each checkpoint with `perception_verify` (not automatic — agent is brain).

## State

`perception_state_save` / `restore` / `list` — cookies + storage for flow resume across steps.

## Auth

`perception_auth_gate` — detect login/MFA/CAPTCHA → `requires_human`, stop automation.

## Playbook

`AGENT_GUIDE.md` §4 (forms), §5 (guards), §6 (multi-step flows).

## Future

- Flow templates as MCP resources
- Auto-checkpoint observe after each `execute_actions` batch
