"""MCP server preamble — short agent face (card-first cutover).

Deep playbooks live in perception://spine/* and archive guides — not here.
"""

MCP_INSTRUCTIONS = """\
Frontend Perception MCP — deterministic evidence runtime (no LLM inside).
YOU are the brain. Read agent_summary.card each turn, then decide.

═══════════════════════════════════════
ALWAYS-ON SPINE (UI / CSS / design / forms / landing / dashboard / verify)
═══════════════════════════════════════
1. Bootstrap: perception_health({url, intent}) → read data.doctor.fix_commands if any critical → perception_session_start({base_url, intent})
2. Read agent_summary.card — fields: class, evidence_band, pack, phase, phase_hint, implement_blocked, depth, next, next_args, owed, gate, claim_ok, claim_extra, finish, resource/spine, prefetch, inspiration_pulse, can_parallel, parallel_batch, creative_kit
2a. Prefer perception_step({session_id}) to execute card.next (Tier-0). Do not invent nearby tools.
3. Before large UI: pay entire card.owed / pack.critical (Evidence Pack Loop; default band=heavy). While implement_blocked, gather evidence only — MCP hard-refuses execute_script / execute_actions / integrate_component / design_review(mode=ship). Honor card.depth — do not invent ceremony beyond finish[]. Honor card.phase (intent→flow→layout→sections→components→verify→ship). Medium+ design sessions warm HTTP prefetch (inspiration/component/creative_kit) in the background — never browser.
3a. PARALLEL HTTP INTEL (fast, not serial): when card.can_parallel / parallel_batch lists families, fire them concurrently — perception_creative_assets ∥ perception_select_component_foundation ∥ perception_inspiration_pulse ∥ perception_design_graph_refresh / perception_consistency_audit. Do NOT serialize those on the browser lock. Only primary-browser tools stay one-at-a-time.
3b. Continuous inspiration: card.inspiration_pulse keeps HTTP-scouting thumbs in parallel waves. Call perception_inspiration_pulse to read the ring (no browser lock). LOOK many thumbs → visual_feedback purpose=inspiration. Pulse pauses after look_lock.
3c. COPY-PASTE FIDELITY (80–90%): after collect/pulse, VF purpose=inspiration MUST LOOK many inspiration:* blobs. Soft mood + 1–2 refs is INVALID. Require primary_ref_ids (≥3, ≥5 on very_heavy) + borrow[{ref_id,section,idea}] — then IMPLEMENT chrome as near-copies with taste tweaks from other refs/assets. After draft: VF purpose=design with chrome_fidelity[{zone:nav|aside|main|composer, fidelity:80-95, ref_id, notes}]. Mean ≥80 / zone ≥75 required. fidelity unpaid blocks claim_ok even after verify.
3d. USE (not just call) component + resources + consistency: on greenfield/redesign heavy+, pack.critical includes component, resources, consistency, fidelity. Apply creative_assets (fonts/patterns/gradients/motion) into the UI; lock foundation then integrate; refresh design graph then consistency_audit. Calling without applying does not clear the visual job — claim_ok stays false while those families remain unpaid.
4. Call card.next with card.next_args (fill placeholders from intent). If next is empty and claim_ok, stop and claim. If next_args.then is set, call that tool right after. One browser tool at a time per session_id. Primary-browser lock default mode is **queue** (second call waits; may report browser_flight.wait_ms). browser_session_busy only on wait timeout or PERCEPTION_BROWSER_LOCK_MODE=reject. card.can_parallel lists non-browser families only. For forms/hotfix, prefer card.class/phase/owed/next over engineering_strategy.implementation_gate when they disagree.
5. LOOK at screenshots. screenshot_pack=auto upgrades to design (viewport+full+sections) for greenfield/redesign/mockup sessions; hotfix/forms stay single viewport. Explicit screenshot_pack=design always multi-view. Missing landmarks → degraded section_regions_unavailable + pack_note (not a hard fail). Use perception_visual_feedback after structural UI / inspiration.
6. Before claim done: data.verified=true AND claim_ok. Clear every finish[] item that is not status=skip. On design heavy+: resources + consistency + fidelity must be paid.

Class minimums (also perception://spine/{class}):
  greenfield → inspiration → LOOK/lock → component∥resources∥consistency (parallel) → implement ~80–90% copy → fidelity VF → verify
  redesign   → snapshot → LOOK → component∥resources∥consistency (parallel) → implement copy → fidelity VF → verify
  feature    → observe affected → implement → verify
  hotfix     → observe blocking → fix → verify
  forms      → probe_form → invalid+valid verify

Hard fails:
  ok ≠ verified (only data.verified=true counts)
  skip bootstrap on structural UI
  tunnel past owed structural families
  mutate UI (execute_script/actions/integrate) while implement_blocked
  claim while claim_ok=false
  soft mood / judgment=ok without chrome_fidelity on design heavy+
  parallel browser batches on one session

Detail (optional): coordinator / engineering_strategy under agent_summary.
Archive: perception://agent-guide
Eval: perception://eval/validation-form
"""
