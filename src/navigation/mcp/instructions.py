"""MCP server preamble — short agent face (card-first cutover).

Deep playbooks live in perception://spine/* and archive guides — not here.
"""

MCP_INSTRUCTIONS = """\
Frontend Perception MCP — deterministic evidence runtime (no LLM inside).
YOU are the brain. Read agent_summary.card each turn, then decide.

═══════════════════════════════════════
ALWAYS-ON SPINE (UI / CSS / design / forms / landing / dashboard / verify)
═══════════════════════════════════════
1. Bootstrap: perception_health({url, intent}) → perception_session_start({base_url, intent})
2. Read agent_summary.card — fields: class, depth, next, next_args, owed, gate, claim_ok, claim_extra, finish, resource
3. Before large UI: pay card.owed (≤3). Honor card.depth (light|standard|full) — do not invent extra ceremony beyond finish[].
4. Call card.next with card.next_args (fill placeholders from intent). If next_args.then is set, call that tool right after. One browser tool at a time per session_id.
5. LOOK at screenshots. Use perception_visual_feedback after structural UI / inspiration.
6. Before claim done: data.verified=true AND claim_ok. Clear every finish[] item that is not status=skip.

Class minimums (also perception://spine/{class}):
  greenfield → inspiration → LOOK/lock → implement → verify
  redesign   → snapshot → LOOK → implement → verify
  feature    → observe affected → implement → verify
  hotfix     → observe blocking → fix → verify
  forms      → probe_form → invalid+valid verify

Hard fails:
  ok ≠ verified (only data.verified=true counts)
  skip bootstrap on structural UI
  tunnel past owed structural families
  claim while claim_ok=false
  parallel browser batches on one session

Detail (optional): coordinator / engineering_strategy under agent_summary.
Archive: perception://agent-guide
Eval: perception://eval/validation-form
"""
