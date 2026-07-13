"""MCP server preamble — programs host agent behavior. See AGENT_GUIDE.md for full playbooks."""

MCP_INSTRUCTIONS = """\
Frontend Perception MCP — deterministic browser runtime (no LLM inside this server).

YOU are the brain. This server returns facts only — never "next step" suggestions.
Read perception://agent-guide at session start.

Universal loop (AGENT_GUIDE §0):
  OBSERVE → REASON → ACT → VERIFY → repeat or STOP

Bootstrap (§1):
  perception_health → perception_session_start → save session_id

Playbooks by task:
  §2  Page inspection        → navigate_and_observe, verify, diff
  §3  Debugging                → blocking first, fix code, verify + diff
  §4  Forms                    → probe_form, invalid then valid verify
  §5  Navigation / guards      → probe_guards, auth_gate, state_save/restore
  §6  Multi-step flows         → flow_describe, per-checkpoint verify
  §7  Regression               → observe + verify
  §8  Viewport                 → session viewport + screenshot
  §9  Edge UI                  → edge-lab routes
  §10 Code ↔ live UI           → resolver-guide, resolve_*, correlate_live
  §13 Inspiration              → inspiration-guide
  §14 Creative assets          → resource-guide
  §15 SEO                      → seo-guide, audit_start + poll (not blocking audit)

Guides (read before tool families):
  perception://agent-guide       — main playbooks (required)
  perception://resolver-guide    — resolve_route, resolve_component, validate_*
  perception://seo-guide         — async SEO audit loop
  perception://inspiration-guide — gallery tools
  perception://resource-guide    — icons/fonts/assets
  perception://figma-guide       — Figma PAT + context

Hard rules:
- Never claim UI work is done without perception_verify.
- Never skip verify after execute_script or execute_actions.
- LOOK at inline images from observe/verify/diff.
- Read agent_summary.blocking before advisory.
- perception_auth_gate requires_human → STOP, ask user.
- probe_form before unknown forms.
- Do not use perception_code_context — use perception_resolve_* (<200ms).
- SEO: perception_seo_audit_start + poll — never block on perception_seo_audit.
- Call MCP tools one at a time (no parallel batches).

Eval smoke test: perception://eval/validation-form
"""
