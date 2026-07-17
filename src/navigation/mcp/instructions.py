"""MCP server preamble — programs host agent behavior. See AGENT_GUIDE.md for full playbooks."""

MCP_INSTRUCTIONS = """\
Frontend Perception MCP — deterministic browser runtime (no LLM inside this server).

YOU are the brain. This server returns facts only — never generic "next step" suggestions.
Read perception://getting-started at session start, then read the focused
resource returned as engineering_strategy.recommended_resource.

Universal loop (AGENT_GUIDE §0):
  STRATEGIZE → OBSERVE → REASON → ACT → VERIFY → repeat or STOP

STRATEGIZE (before planning):
  Read agent_summary.engineering_strategy on health and session_start.
  Resolve unresolved structural decisions before broad implementation.
  Evidence and tools serve engineering decisions — not the other way around.

Bootstrap (§1):
  perception_health → perception_session_start({ base_url, intent }) → save session_id

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
  §14 Inspiration              → inspiration-guide
  §15 Creative assets          → resource-guide
  §16 SEO                      → seo-guide; dev audit_start inline, pro start + poll

Methodology resources (progressive disclosure):
  perception://getting-started       — bootstrap and resource routing
  perception://frontend-methodology  — universal decision-led loop
  perception://design-workflow       — greenfield structural UI
  perception://redesign-workflow     — measured redesign + SpecDiff
  perception://bugfix-workflow       — surgical observe/fix/verify
  perception://engineering-strategy  — strategy and implementation gate
  perception://decision-ledger       — evidence and ship challenge lifecycle
  perception://ship-council          — post-verify ship gate (design_review mode=ship)
  perception://verification-guide    — post-action verification and Spec gate
  perception://browser-lifecycle     — single-owner browser restoration
  perception://agent-guide           — compatibility index

Specialist guides:
  perception://resolver-guide    — resolve_route, resolve_component, validate_*
  perception://seo-guide         — Development (inline) vs Professional (poll) SEO
  perception://inspiration-guide — gallery tools
  perception://resource-guide    — icons/fonts/assets
  perception://figma-guide       — Figma PAT + context

Hard rules:
- Top-level ok means tool transport completed; it does not prove usable evidence.
  For verify, only data.verified=true counts as a pass.
- While implementation_gate.state=blocked, obey prohibited_actions and run
  next_required_capability. Never invent a blocked structural decision.
- Only coordination_evidence.advancement_eligible=true may resolve/advance evidence.
- Never claim UI work is done without the Done ladder: data.verified=true, then
  section checklist (observe→verify each block when section_checklist_required),
  then Ship Council clear when ship_council_required. Verify alone is not claim-done
  for design_driven / redesign / structural drafts.
- Never skip verify after execute_script or execute_actions.
- LOOK at inline images from observe/verify/diff.
- Read agent_summary.blocking before advisory.
- After drafting UI vs a bound reference Spec: remeasure with perception_build_design_snapshot and honor spec_revision_gate (revision_required → revise drifts).
- perception_auth_gate requires_human → STOP, ask user.
- probe_form before unknown forms.
- Do not use perception_code_context — use perception_resolve_* (<200ms).
- SEO: development — perception_seo_audit_start only (scan_id required); professional — start + poll. Never block on perception_seo_audit.
- Call MCP tools **one at a time** (no parallel batches on one session_id).
- observe detail: summary_only (default) | full (console/network entries) | metadata_only (lightest).
- Reuse scan_id from observe for seo_audit_start (dev) and diff.

Tool groups (tools/list _meta.group): Session, Browser, Quality, Resolver, Component, Design, SEO, Resources, Inspiration, Figma, Diagnostics, Coordinator.

Eval smoke test: perception://eval/validation-form
"""
