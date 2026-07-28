"""Hard adversarial agent-face matrix — classify + card next/claim invariants.

Goes beyond the 4-case happy board: ambiguous intents, stamped scopes that
conflict with cues, done-state traps, claim_extra ceremony, and empty portfolios.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.coordinator_card import (  # noqa: E402
	build_agent_face_card,
	classify_agent_face,
)

OUT = ROOT / "docs/research/agent_face_hard_matrix.json"


def _row(
	*,
	id: str,
	intent: str,
	expect_class: str,
	expect_next: str | set[str] | None = None,
	forbid_next: set[str] | None = None,
	expect_claim_ok: bool | None = None,
	forbid_owed: set[str] | None = None,
	require_owed0: str | None = None,
	strategy_extra: dict | None = None,
) -> dict:
	return {
		"id": id,
		"intent": intent,
		"expect_class": expect_class,
		"expect_next": expect_next,
		"forbid_next": forbid_next or set(),
		"expect_claim_ok": expect_claim_ok,
		"forbid_owed": forbid_owed or set(),
		"require_owed0": require_owed0,
		"strategy_extra": strategy_extra or {},
	}


CASES = [
	# --- Ambiguous / conflicting stamps ---
	_row(
		id="fix_vs_feature_stamp",
		intent="Fix overlapping mobile menu button",
		expect_class="hotfix",
		expect_next="perception_navigate_and_observe",
		strategy_extra={
			"task_scope": "feature_incremental",
			"right_sizing": {"tier": "polish"},
			"influence_level": "balanced",
		},
	),
	_row(
		id="settings_toggle_feature",
		intent="Add a settings toggle to an existing page",
		expect_class="feature",
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration"},
		strategy_extra={
			"task_scope": "feature_incremental",
			"right_sizing": {"tier": "polish"},
			"influence_level": "balanced",
		},
	),
	_row(
		id="polish_under_design_driven",
		intent="Tighten spacing on the navbar only — visual polish",
		expect_class="hotfix",
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration", "snapshot"},
		strategy_extra={
			"task_scope": "design_driven",
			"right_sizing": {"tier": "polish"},
			"influence_level": "structural",
		},
	),
	_row(
		id="landing_with_signup_not_forms",
		intent="Build a new SaaS landing page with strong brand hero and email signup in the footer",
		expect_class="greenfield",
		# Current classifier may over-capture forms — record expected preferred class
		expect_next=None,  # class assertion only until we decide forms vs greenfield
		strategy_extra={"influence_level": "structural"},
	),
	_row(
		id="reference_image_redesign",
		intent="Match this uploaded reference image to the hero section",
		expect_class="redesign",
		expect_next={
			"perception_navigate_and_observe",
			"perception_build_design_snapshot",
		},
		forbid_next={"perception_inspiration_collect"},
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "observe", "suggested": "perception_navigate_and_observe"},
				],
			},
		},
	),
	_row(
		id="forms_vs_component_gate",
		intent="Verify /forms/validation invalid then valid submit",
		expect_class="forms",
		expect_next="perception_probe_form",
		forbid_owed={"component", "inspiration"},
		strategy_extra={
			"task_scope": "feature_incremental",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "component_search_plan",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {"paid": [], "unpaid": []},
		},
	),
	_row(
		id="feature_plus_fix_in_sentence",
		intent="Add a pricing feature to the existing checkout page",
		expect_class="feature",
		# "fix" is absent — should stay feature
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration"},
		strategy_extra={"task_scope": "feature_incremental", "influence_level": "balanced"},
	),
	_row(
		id="add_feature_to_fix_copy",
		intent="Add a feature to fix checkout copy on the existing page",
		# Contains both feature and fix — surgical fix cue currently wins (hotfix)
		expect_class="hotfix",
		expect_next="perception_navigate_and_observe",
		strategy_extra={"task_scope": "feature_incremental", "influence_level": "balanced"},
	),
	# --- Done-state / claim traps ---
	_row(
		id="forms_done_no_respine",
		intent="Verify /forms/validation",
		expect_class="forms",
		expect_next="",
		expect_claim_ok=True,
		strategy_extra={
			"task_scope": "forms",
			"verification_status": "passed",
			"implementation_gate": {"state": "ready", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [{"family": "verify"}],
				"unpaid": [],
			},
		},
	),
	_row(
		id="ship_blocks_claim",
		intent="Ship the landing page",
		expect_class="greenfield",
		expect_next="perception_design_review",
		expect_claim_ok=False,
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"verification_status": "passed",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": [],
				"ship_council_required": True,
			},
			"episode_portfolio": {
				"paid": [{"family": "verify"}, {"family": "inspiration"}],
				"unpaid": [],
			},
		},
	),
	_row(
		id="section_after_verify",
		intent="Landing page sections checklist",
		expect_class="greenfield",
		expect_next="perception_observe",
		expect_claim_ok=False,
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"verification_status": "passed",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": [],
				"section_checklist_required": True,
			},
			"episode_portfolio": {"paid": [{"family": "verify"}], "unpaid": []},
		},
	),
	_row(
		id="spec_revision_remeasure",
		intent="Match mockup after draft",
		expect_class="redesign",
		expect_next="perception_build_design_snapshot",
		expect_claim_ok=False,
		strategy_extra={
			"task_scope": "redesign",
			"influence_level": "structural",
			"verification_status": "passed",
			"spec_revision_gate": {"revision_required": True},
			"implementation_gate": {"state": "ready", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [{"family": "verify"}, {"family": "snapshot"}],
				"unpaid": [],
			},
		},
	),
	_row(
		id="plan_component_remaps",
		intent="Build pricing section foundation",
		expect_class="greenfield",
		expect_next="perception_select_component_foundation",
		forbid_next={"perception_plan_component_search"},
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "blocked",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [
					{"family": "inspiration"},
					{"family": "visual_feedback"},
					{"family": "snapshot"},
				],
				"unpaid": [
					{
						"family": "component",
						"suggested": "perception_plan_component_search",
					}
				],
			},
		},
	),
	_row(
		id="greenfield_priority_inspiration_first",
		intent="New SaaS landing with brand hero",
		expect_class="greenfield",
		expect_next="perception_inspiration_collect",
		require_owed0="inspiration",
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"implementation_gate": {
				"state": "blocked",
				"prohibited_actions": ["claim_complete"],
				"ship_council_required": True,
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "component", "suggested": "perception_select_component_foundation"},
					{"family": "verify", "suggested": "perception_verify"},
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
				],
			},
		},
	),
	# --- Deeper ambiguity / trap cases ---
	_row(
		id="auth_login_is_forms",
		intent="Verify login form at /forms/login: invalid then valid submit",
		expect_class="forms",
		expect_next="perception_probe_form",
		strategy_extra={"influence_level": "balanced"},
	),
	_row(
		id="redesign_checkout_stays_redesign",
		intent="Redesign the checkout layout to match the mockup — measured redesign",
		expect_class="redesign",
		expect_next={
			"perception_navigate_and_observe",
			"perception_build_design_snapshot",
		},
		forbid_next={"perception_probe_form"},
		strategy_extra={
			"task_scope": "redesign",
			"influence_level": "structural",
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "observe", "suggested": "perception_navigate_and_observe"},
				],
			},
		},
	),
	_row(
		id="mockup_match_not_inspiration",
		intent="Match this mockup screenshot for the pricing page",
		expect_class="redesign",
		forbid_next={"perception_inspiration_collect"},
		expect_next={
			"perception_navigate_and_observe",
			"perception_build_design_snapshot",
		},
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "observe", "suggested": "perception_navigate_and_observe"},
				],
			},
		},
	),
	_row(
		id="claim_extra_blocks_claim",
		intent="Landing page ready to ship",
		expect_class="greenfield",
		expect_claim_ok=False,
		forbid_next={""},  # must still point at unpaid ceremony
		strategy_extra={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"verification_status": "passed",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": [],
				"ship_council_required": True,
			},
			"episode_portfolio": {
				"paid": [{"family": "verify"}],
				"unpaid": [],
			},
		},
	),
	_row(
		id="polish_spacing_not_greenfield",
		intent="Polish the footer spacing only — chrome tweak",
		expect_class="hotfix",
		forbid_owed={"inspiration", "snapshot"},
		expect_next="perception_navigate_and_observe",
		strategy_extra={
			"task_scope": "design_driven",
			"right_sizing": {"tier": "polish"},
			"influence_level": "structural",
		},
	),
	_row(
		id="host_polish_advisory_not_feature_steal",
		intent="Add a pricing feature to the existing checkout page",
		expect_class="feature",
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration"},
		strategy_extra={
			"task_scope": "feature_incremental",
			"influence_level": "balanced",
			"host_action": "RIGHT-SIZE POLISH: pay browser_observe, visual_feedback, browser_verify.",
			"summary": "Verification outcome is unresolved. Scope=feature_incremental.",
		},
	),
	_row(
		id="feature_survives_debug_scope",
		intent="Add a settings toggle to an existing page — incremental feature",
		expect_class="feature",
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration"},
		strategy_extra={
			# Observe often rewrites task_scope to debug via cluster.debug.*
			"task_scope": "debug",
			"influence_level": "maintenance",
			"summary": "Observed homepage; continue incremental work",
			"host_action": "Gather observe evidence then verify",
		},
	),
	_row(
		id="feature_empty_portfolio_observe",
		intent="Add dark mode toggle to settings",
		expect_class="feature",
		expect_next="perception_navigate_and_observe",
		forbid_next={"perception_verify", "perception_inspiration_collect"},
		expect_claim_ok=False,
		strategy_extra={
			"task_scope": "feature_incremental",
			"influence_level": "balanced",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {"paid": [], "unpaid": []},
		},
	),
	_row(
		id="hotfix_empty_portfolio_observe",
		intent="CSS bug: CTA overlaps footer on mobile",
		expect_class="hotfix",
		expect_next="perception_navigate_and_observe",
		forbid_owed={"inspiration", "component"},
		strategy_extra={
			"task_scope": "feature_incremental",
			"influence_level": "balanced",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": ["claim_complete"],
				"next_required_capability": "inspiration_workflow",
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
				],
			},
		},
	),
	_row(
		id="login_nav_landing_stays_greenfield",
		intent="Build a new product landing with brand hero; login link only in the nav",
		expect_class="greenfield",
		forbid_next={"perception_probe_form"},
		strategy_extra={"influence_level": "structural"},
	),
	_row(
		id="auth_probe_stays_forms",
		intent="Invalid then valid submit on the auth login form at /forms/login",
		expect_class="forms",
		expect_next="perception_probe_form",
		strategy_extra={"influence_level": "balanced"},
	),
	_row(
		id="claim_ok_after_verify_hotfix",
		intent="Fix overlapping CTA — surgical CSS hotfix",
		expect_class="hotfix",
		expect_next="",
		expect_claim_ok=True,
		strategy_extra={
			"task_scope": "hotfix",
			"influence_level": "minimal",
			"verification_status": "passed",
			"implementation_gate": {"state": "maintenance", "prohibited_actions": []},
			"episode_portfolio": {"paid": [{"family": "verify"}], "unpaid": []},
		},
	),
]


def _run_one(case: dict) -> dict:
	extra = dict(case["strategy_extra"])
	portfolio = extra.pop("episode_portfolio", None)
	gate = extra.pop("implementation_gate", None)
	strategy = {
		"intent": case["intent"],
		"verification_status": extra.pop("verification_status", "pending"),
		"implementation_gate": gate
		or {
			"state": "ready",
			"prohibited_actions": ["claim_complete"],
		},
		"episode_portfolio": portfolio or {"paid": [], "unpaid": []},
		"recommended_resource": "perception://getting-started",
		**extra,
	}
	# Keep intent in strategy for classify
	face = build_agent_face_card(episode_id=f"hard_{case['id']}", strategy=strategy)
	cls = face["class"]
	nxt = face["next"]
	owed_fams = [o["family"] for o in face["owed"]]

	checks: dict[str, bool] = {}
	checks["class"] = cls == case["expect_class"]
	en = case["expect_next"]
	if en is None:
		checks["next"] = True
	elif isinstance(en, set):
		checks["next"] = nxt in en
	else:
		checks["next"] = nxt == en
	fn = case["forbid_next"]
	checks["forbid_next"] = nxt not in fn
	if case["expect_claim_ok"] is None:
		checks["claim_ok"] = True
	else:
		checks["claim_ok"] = face["claim_ok"] is case["expect_claim_ok"]
	fo = case["forbid_owed"]
	checks["forbid_owed"] = not any(f in fo for f in owed_fams)
	if case["require_owed0"]:
		checks["owed0"] = bool(owed_fams) and owed_fams[0] == case["require_owed0"]
	else:
		checks["owed0"] = True

	# Soft note for landing+signup (document current behavior)
	note = None
	if case["id"] == "landing_with_signup_not_forms" and cls != "greenfield":
		note = f"over_capture: got class={cls} (prefer greenfield for hero landing)"

	passed = all(checks.values())
	return {
		"id": case["id"],
		"passed": passed,
		"class": cls,
		"next": nxt,
		"owed": owed_fams,
		"claim_ok": face["claim_ok"],
		"depth": face["depth"],
		"checks": checks,
		"note": note,
		"classify": classify_agent_face(strategy),
	}


def main() -> int:
	rows = [_run_one(c) for c in CASES]
	# landing_with_signup is advisory in this pass — fail hard only if we want greenfield locked
	hard = [r for r in rows if r["id"] != "landing_with_signup_not_forms"]
	# Still report landing as soft fail in board if wrong
	soft = [r for r in rows if r["id"] == "landing_with_signup_not_forms"]
	for r in soft:
		if r["class"] != "greenfield":
			r["passed"] = False
			r["checks"]["class"] = False

	ok = all(r["passed"] for r in rows)
	payload = {
		"ok": ok,
		"passed": sum(1 for r in rows if r["passed"]),
		"total": len(rows),
		"rows": rows,
	}
	OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	for r in rows:
		status = "PASS" if r["passed"] else "FAIL"
		extra = f" note={r['note']}" if r.get("note") else ""
		print(
			f"[{status}] {r['id']}: class={r['class']} next={r['next']!r} "
			f"owed={r['owed']} claim_ok={r['claim_ok']}{extra}"
		)
	print(f"BOARD: {'PASS' if ok else 'FAIL'} ({payload['passed']}/{payload['total']})")
	print(f"Wrote {OUT}")
	return 0 if ok else 1


if __name__ == "__main__":
	raise SystemExit(main())
