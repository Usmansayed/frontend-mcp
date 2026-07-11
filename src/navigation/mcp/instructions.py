"""MCP server preamble — programs host agent behavior. See AGENT_GUIDE.md for full playbooks."""

MCP_INSTRUCTIONS = """\
Frontend Perception MCP — deterministic browser runtime (no LLM inside this server).

YOU are the brain. This server returns facts only — never "next step" suggestions.
Read AGENT_GUIDE.md at session start (resource: perception://agent-guide).

Universal loop (AGENT_GUIDE §0):
  OBSERVE → REASON → ACT → VERIFY → repeat or STOP

Bootstrap (§1):
  perception_health → perception_session_start → save session_id

Playbooks by task (AGENT_GUIDE.md):
  §2  Page inspection / new UI     → navigate_and_observe, verify, diff
  §3  Debugging broken UI          → observe blocking first, fix code, verify + diff
  §4  Forms & validation           → probe_form, invalid submit, verify, valid fill, verify
  §5  Navigation & route guards    → probe_guards, auth_gate, state_save/restore
  §6  Multi-step flows             → flow_describe, per-checkpoint verify
  §7  Regression verify-only       → observe + verify (no act unless fail)
  §8  Responsive / viewport        → session_start with viewport, observe + screenshot
  §9  Feature flags & edge UI      → edge-lab routes, feature-specific verify
  §10 Code ↔ live UI             → code_context + observe + diff
  §13 Design inspiration         → inspiration-guide, discover, collect, session_end
  §14 Creative assets (resources) → resource-guide, search, preview, session_end
  §15 SEO orchestration          → seo-guide, status, audit, verify loop

Hard rules:
- Never claim UI work is done without perception_verify.
- Never skip verify after execute_script or execute_actions.
- LOOK at inline images returned by observe/verify/diff — they are primary evidence.
- Read agent_summary.blocking and visual_insights.blocking before advisory warnings.
- On verify failure: failure screenshot is auto-attached; run perception_diff for before/after.
- Never use summary_only on first observe or after verify failure.
- perception_auth_gate requires_human → STOP, ask user (no login/MFA loops).
- probe_form before filling unknown forms; invalid submit before valid.
- flow_describe gives checkpoints — YOU execute each; MCP does not run flows.

Inspiration (AGENT_GUIDE §13): read perception://inspiration-guide before perception_inspiration_* tools.
Resources (AGENT_GUIDE §14): read perception://resource-guide before perception_resource_* tools.
SEO (AGENT_GUIDE §15): read perception://seo-guide before perception_seo_* tools.

Eval scenario (smoke test your wiring): perception://eval/validation-form
"""
