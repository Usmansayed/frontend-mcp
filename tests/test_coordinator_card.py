# tests/test_coordinator_card.py
from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.coordinator_card import (
    build_coordinator_card,
    strategy_fingerprint,
)

@pytest.mark.unit
def test_build_agent_face_card_simple_spine():
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
        classify_agent_face,
    )

    strategy = {
        "task_scope": "design_driven",
        "influence_level": "structural",
        "host_action": "Collect inspiration",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete", "broad_visual_implementation"],
            "section_checklist_required": False,
            "ship_council_required": True,
        },
        "episode_portfolio": {
            "paid": [],
            "unpaid": [
                {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                {"family": "visual_feedback", "suggested": "perception_visual_feedback"},
                {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
                {"family": "verify", "suggested": "perception_verify"},
            ],
        },
        "recommended_resource": "perception://getting-started",
    }
    assert classify_agent_face(strategy) == "greenfield"
    face = build_agent_face_card(episode_id="ep_face", strategy=strategy)
    assert face["schema"] == "agent_face_card.v1"
    assert face["class"] == "greenfield"
    assert face["next"] == "perception_inspiration_collect"
    assert len(face["owed"]) == 3
    assert face["owed"][0]["family"] == "inspiration"
    assert face["gate"] == "blocked"
    assert face["claim_ok"] is False
    assert "ship_council" in face["claim_extra"]
    assert face["resource"] == "perception://spine/greenfield"
    assert isinstance(face.get("next_args"), dict)
    orders = face.get("orders") or []
    assert orders, face
    assert any("80–90%" in o or "80-90%" in o for o in orders)
    assert any("implement_blocked" in o for o in orders)
    assert "query" in face["next_args"]


@pytest.mark.unit
def test_promote_surfaces_agent_summary_card() -> None:
    from navigation.coordination_intelligence.planning.engineering_strategy import (
        promote_coordinator_visibility,
    )

    envelope: dict = {
        "data": {
            "engineering_strategy": {
                "task_scope": "hotfix",
                "influence_level": "surgical",
                "host_action": "Observe then fix",
                "verification_status": "passed",
                "implementation_gate": {
                    "state": "ready",
                    "prohibited_actions": [],
                },
                "episode_portfolio": {
                    "paid": [{"family": "verify"}, {"family": "observe"}],
                    "unpaid": [],
                },
                "recommended_resource": "perception://bugfix-workflow",
            }
        }
    }
    card = {
        "episode_id": "ep_h",
        "host_action": "Observe then fix",
        "gate": {"state": "ready", "prohibited_actions": []},
        "portfolio": {"paid": ["verify", "observe"], "unpaid": []},
        "suggested_capability": "observe",
    }
    promote_coordinator_visibility(envelope, card)
    face = envelope["agent_summary"]["card"]
    assert face["class"] == "hotfix"
    assert face["next"] == ""
    assert face["claim_ok"] is True
    assert envelope["agent_summary"]["recommended_next"] == face["next"]


@pytest.mark.unit
def test_face_done_state_does_not_respine() -> None:
    """G1: after verify + empty claim_extra, do not re-spine probe/observe forever."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    forms = build_agent_face_card(
        episode_id="ep_done_forms",
        strategy={
            "task_scope": "forms",
            "intent": "Verify /forms/validation",
            "influence_level": "minimal",
            "verification_status": "passed",
            "implementation_gate": {"state": "ready", "prohibited_actions": []},
            "episode_portfolio": {
                "paid": [{"family": "forms"}, {"family": "verify"}],
                "unpaid": [],
            },
            "recommended_resource": "perception://spine/forms",
        },
    )
    assert forms["class"] == "forms"
    assert forms["claim_ok"] is True
    assert forms["claim_extra"] == []
    assert forms["next"] == ""
    assert forms["next"] != "perception_probe_form"

    hotfix = build_agent_face_card(
        episode_id="ep_done_hf",
        strategy={
            "task_scope": "hotfix",
            "intent": "fix overlapping CTA",
            "influence_level": "surgical",
            "verification_status": "passed",
            "implementation_gate": {"state": "ready", "prohibited_actions": []},
            "episode_portfolio": {
                "paid": [{"family": "observe"}, {"family": "verify"}],
                "unpaid": [],
            },
            "recommended_resource": "perception://spine/hotfix",
        },
    )
    assert hotfix["class"] == "hotfix"
    assert hotfix["claim_ok"] is True
    assert hotfix["next"] == ""
    assert hotfix["next"] != "perception_navigate_and_observe"

    # Empty portfolio after verify must not re-inject forms owed.
    forms_empty = build_agent_face_card(
        episode_id="ep_done_forms_empty",
        strategy={
            "task_scope": "forms",
            "intent": "Verify /forms/validation",
            "verification_status": "passed",
            "implementation_gate": {"state": "ready", "prohibited_actions": []},
            "episode_portfolio": {"paid": [{"family": "verify"}], "unpaid": []},
        },
    )
    assert forms_empty["claim_ok"] is True
    assert forms_empty["next"] == ""
    assert "forms" not in {o["family"] for o in forms_empty["owed"]}


@pytest.mark.unit
def test_face_claim_ok_false_when_claim_extra_even_if_gate_allows() -> None:
    """G2: claim_extra alone must block claim_ok (gate may omit claim_complete)."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_ship_extra",
        strategy={
            "task_scope": "design_driven",
            "intent": "Ship the landing page",
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
            "recommended_resource": "perception://spine/greenfield",
        },
    )
    assert "ship_council" in face["claim_extra"]
    assert face["claim_ok"] is False
    assert face["next"] == "perception_design_review"
    assert face["next_args"].get("mode") == "ship"


@pytest.mark.unit
def test_face_polish_not_greenfield_under_design_driven() -> None:
    """G3: polish/chrome must not inherit greenfield full inspiration ladder."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
        classify_agent_face,
    )

    strategy = {
        "task_scope": "design_driven",
        "intent": "Polish navbar spacing only — tighten chrome",
        "influence_level": "structural",
        "right_sizing": {"tier": "polish"},
        "verification_status": "pending",
        "implementation_gate": {
            "state": "ready",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_portfolio": {
            "paid": [],
            "unpaid": [{"family": "observe", "suggested": "perception_navigate_and_observe"}],
        },
        "recommended_resource": "perception://design-workflow",
    }
    assert classify_agent_face(strategy) == "hotfix"
    face = build_agent_face_card(episode_id="ep_polish", strategy=strategy)
    assert face["class"] == "hotfix"
    assert face["depth"] != "full"
    assert face["resource"] == "perception://spine/hotfix"
    finish_ids = {row["id"] for row in face["finish"]}
    assert "inspiration" not in finish_ids or any(
        row["id"] == "inspiration" and row["status"] == "skip" for row in face["finish"]
    )


@pytest.mark.unit
def test_face_host_action_polish_does_not_steal_feature() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "task_scope": "feature_incremental",
                "influence_level": "balanced",
                "intent": "Add a pricing feature to the existing checkout page",
                "host_action": "RIGHT-SIZE POLISH: pay browser_observe, visual_feedback, browser_verify.",
                "summary": "Verification outcome is unresolved. Scope=feature_incremental.",
            }
        )
        == "feature"
    )


@pytest.mark.unit
def test_face_feature_survives_debug_scope_after_observe() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
        build_agent_face_card,
    )

    assert (
        classify_agent_face(
            {
                "task_scope": "debug",
                "influence_level": "maintenance",
                "intent": "Add a settings toggle to an existing page — incremental feature",
                "summary": "Observed homepage",
                "host_action": "Gather observe evidence",
            }
        )
        == "feature"
    )
    # Additive without the words "feature"/"toggle" still survives debug stamp.
    bell = {
        "task_scope": "debug",
        "influence_level": "surgical",
        "intent": "Add a notifications bell to the existing header",
        "verification_status": "pending",
        "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
        "episode_portfolio": {"paid": [], "unpaid": []},
    }
    assert classify_agent_face(bell) == "feature"
    face = build_agent_face_card(episode_id="ep_bell_debug", strategy=bell)
    assert face["class"] == "feature"
    assert face["evidence_band"] == "heavy"


@pytest.mark.unit
def test_face_trailing_soft_fix_does_not_steal_additive_feature() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
        build_agent_face_card,
    )

    strategy = {
        "task_scope": "feature_incremental",
        "influence_level": "balanced",
        "intent": "Add a settings toggle — then fix any spacing if needed",
        "verification_status": "pending",
        "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
        "episode_portfolio": {"paid": [], "unpaid": []},
    }
    assert classify_agent_face(strategy) == "feature"
    face = build_agent_face_card(episode_id="ep_trail_fix", strategy=strategy)
    assert face["class"] == "feature"
    assert face["evidence_band"] == "heavy"
    assert all(o["family"] != "inspiration" for o in face["owed"])


@pytest.mark.unit
def test_live_a02_redesign_beats_greenfield_policy() -> None:
    """Live kit A02: mockup redesign must stay redesign under design.greenfield.*."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_a02",
        strategy={
            "intent": "Redesign the dashboard to match this mockup — measure first",
            "task_scope": "design_driven",
            "influence_level": "structural",
            "policy_id": "design.greenfield.no_refs.early",
            "implementation_gate": {
                "state": "blocked",
                "next_required_capability": "inspiration_workflow",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [],
                "unpaid": [
                    {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                    {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
                    {"family": "observe", "suggested": "perception_navigate_and_observe"},
                ],
            },
        },
    )
    assert face["class"] == "redesign"
    assert face["next"] in {
        "perception_navigate_and_observe",
        "perception_build_design_snapshot",
    }
    assert face["next"] != "perception_inspiration_collect"


@pytest.mark.unit
def test_live_g04_feature_beats_greenfield_policy() -> None:
    """Live kit G04: add block on existing must stay feature under greenfield policy."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_g04",
        strategy={
            "intent": "Add a pricing comparison block to the existing marketing page",
            "task_scope": "feature_incremental",
            "influence_level": "structural",
            "policy_id": "design.greenfield.no_refs.early",
            "implementation_gate": {
                "state": "blocked",
                "next_required_capability": "inspiration_workflow",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [],
                "unpaid": [
                    {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                    {"family": "observe", "suggested": "perception_navigate_and_observe"},
                ],
            },
        },
    )
    assert face["class"] == "feature"
    assert face["evidence_band"] == "heavy"
    assert all(o["family"] != "inspiration" for o in face["owed"])


@pytest.mark.unit
def test_live_d01_claim_ok_despite_claim_complete_lag() -> None:
    """Live kit D01: verified hotfix may claim even if claim_complete still prohibited."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_d01",
        strategy={
            "intent": "Fix overlapping CTA",
            "task_scope": "hotfix",
            "influence_level": "surgical",
            "verification_status": "passed",
            "implementation_gate": {
                "state": "ready",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [{"family": "observe"}, {"family": "verify"}],
                "unpaid": [],
            },
        },
    )
    assert face["class"] == "hotfix"
    assert face["next"] == ""
    assert face["claim_ok"] is True


@pytest.mark.unit
def test_face_feature_intent_without_stamp() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "intent": "Add a pricing feature to the existing checkout page",
            }
        )
        == "feature"
    )


@pytest.mark.unit
def test_face_redesign_checkout_not_forms() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "task_scope": "redesign",
                "intent": "Redesign the checkout layout to match the mockup — measured redesign",
                "influence_level": "structural",
            }
        )
        == "redesign"
    )


@pytest.mark.unit
def test_face_landing_signup_stays_greenfield() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "intent": "Build a new SaaS landing page with strong brand hero and email signup in the footer",
                "influence_level": "structural",
            }
        )
        == "greenfield"
    )


@pytest.mark.unit
def test_face_checkout_feature_not_forms() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "task_scope": "feature_incremental",
                "intent": "Add a pricing feature to the existing checkout page",
                "influence_level": "balanced",
            }
        )
        == "feature"
    )


@pytest.mark.unit
def test_face_fix_checkout_copy_not_forms() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
    )

    assert (
        classify_agent_face(
            {
                "task_scope": "feature_incremental",
                "intent": "Add a feature to fix checkout copy on the existing page",
                "influence_level": "balanced",
            }
        )
        == "hotfix"
    )


@pytest.mark.unit
def test_face_vague_design_fix_routes_to_redesign() -> None:
	"""Vague 'fix the design/footer/look' is redesign — not surgical hotfix."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
		classify_agent_face,
		_design_fix_intent_cues,
	)

	cases = (
		"fix the footer",
		"fix the design",
		"fix how it looks",
		"make it look better",
		"fix the hero section",
		"just fix it",
		"the landing page looks cheap — fix the look",
	)
	for intent in cases:
		assert _design_fix_intent_cues(intent), intent
		strategy = {
			"task_scope": "feature_incremental",
			"intent": intent,
			"influence_level": "balanced",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "design_snapshot",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "observe", "suggested": "perception_navigate_and_observe"},
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
				],
			},
		}
		assert classify_agent_face(strategy) == "redesign", intent
		face = build_agent_face_card(episode_id="ep_design_fix", strategy=strategy)
		assert face["class"] == "redesign", intent
		assert face["resource"] == "perception://spine/redesign", intent
		assert face["evidence_band"] in {"heavy", "very_heavy"}, intent


@pytest.mark.unit
def test_face_defect_fix_stays_hotfix_not_design_fix() -> None:
	"""Broken/overlapping/bug language must stay hotfix despite 'fix'."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
		classify_agent_face,
		_design_fix_intent_cues,
	)

	cases = (
		"fix overlapping mobile menu button",
		"fix the broken footer layout",
		"fix css bug on the hero",
		"production hotfix for broken login button",
		"fix one button padding from 14px to 15px",
	)
	for intent in cases:
		assert not _design_fix_intent_cues(intent), intent
		strategy = {
			"task_scope": "feature_incremental",
			"intent": intent,
			"influence_level": "balanced",
			"implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
			"episode_portfolio": {"paid": [], "unpaid": []},
		}
		assert classify_agent_face(strategy) == "hotfix", intent
		face = build_agent_face_card(episode_id="ep_defect", strategy=strategy)
		assert face["class"] == "hotfix", intent


@pytest.mark.unit
def test_face_hotfix_cues_beat_stamped_feature_incremental() -> None:
    """Intent 'fix overlapping…' must stay hotfix even if scope is feature_incremental."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
        build_agent_face_card,
    )

    strategy = {
        "task_scope": "feature_incremental",
        "intent": "fix overlapping mobile menu button",
        "influence_level": "balanced",
        "right_sizing": {"tier": "polish"},
        "verification_status": "pending",
        "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
        "episode_portfolio": {"paid": [], "unpaid": []},
    }
    assert classify_agent_face(strategy) == "hotfix"
    face = build_agent_face_card(episode_id="ep_hf_stamp", strategy=strategy)
    assert face["class"] == "hotfix"
    assert face["resource"] == "perception://spine/hotfix"
    assert face["next"] == "perception_navigate_and_observe"


@pytest.mark.unit
def test_face_run6_advisory_fix_prose_does_not_poison_greenfield() -> None:
	"""Run 6 P0: summary/matters saying 'fix' must not flip design_driven → hotfix."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
		classify_agent_face,
	)

	strategy = {
		"task_scope": "design_driven",
		"intent": "structural hardcore coordination review",
		"summary": "Keep MCP lightweight: observe, fix, verify. Skip design exploration.",
		"what_matters_now": ["Minimize scope; observe, fix, verify, ship"],
		"influence_level": "structural",
		"right_sizing": {"tier": "initiative"},
		"policy_id": "design.greenfield.no_refs.early",
		"implementation_gate": {
			"state": "blocked",
			"next_required_capability": "inspiration_workflow",
			"prohibited_actions": ["claim_complete", "broad_visual_implementation"],
			"section_checklist_required": False,
		},
		"episode_portfolio": {
			"paid": [],
			"unpaid": [
				{"family": "inspiration", "suggested": "perception_inspiration_collect"},
				{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
				{"family": "component", "suggested": "perception_select_component_foundation"},
				{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
			],
		},
		"recommended_resource": "perception://guide/inspiration",
	}
	assert classify_agent_face(strategy) == "greenfield"
	face = build_agent_face_card(episode_id="ep_run6_struct", strategy=strategy)
	assert face["class"] == "greenfield"
	assert face["resource"] == "perception://spine/greenfield"
	assert face["next"] == "perception_inspiration_collect"
	owed_fams = [o["family"] for o in face["owed"]]
	assert "inspiration" in owed_fams
	assert owed_fams != ["visual_feedback"]
	by_id = {row["id"]: row for row in face["finish"]}
	assert by_id["section_checklist"]["status"] == "skip"


@pytest.mark.unit
def test_face_run6_form_validation_beats_feature_stamp() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		classify_agent_face,
		build_agent_face_card,
	)

	strategy = {
		"task_scope": "feature_incremental",
		"intent": "Wire up the contact form validation",
		"influence_level": "balanced",
		"right_sizing": {"tier": "polish"},
		"implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
		"episode_portfolio": {"paid": [], "unpaid": []},
	}
	assert classify_agent_face(strategy) == "forms"
	face = build_agent_face_card(episode_id="ep_run6_forms", strategy=strategy)
	assert face["class"] == "forms"
	assert face["resource"] == "perception://spine/forms"
	assert face["next"] == "perception_probe_form"


@pytest.mark.unit
def test_face_run6b_greenfield_policy_forces_class_and_owed() -> None:
	"""Retest A/J: design.greenfield + unpaid structural must not stay hotfix LOOK-only."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
		classify_agent_face,
	)

	strategy = {
		"task_scope": "design_driven",
		"intent": "structural hardcore coordination review",
		"influence_level": "structural",
		"policy_id": "design.greenfield.no_refs.early",
		"right_sizing": {"tier": "initiative"},
		"implementation_gate": {
			"state": "blocked",
			"next_required_capability": "inspiration_workflow",
			"prohibited_actions": ["claim_complete"],
		},
		"episode_portfolio": {
			"paid": [],
			"unpaid": [
				{"family": "inspiration", "suggested": "perception_inspiration_collect"},
				{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
				{"family": "component", "suggested": "perception_select_component_foundation"},
				{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
			],
		},
	}
	assert classify_agent_face(strategy) == "greenfield"
	face = build_agent_face_card(episode_id="ep_run6b_a", strategy=strategy)
	assert face["class"] == "greenfield"
	assert face["next"] == "perception_inspiration_collect"
	assert [o["family"] for o in face["owed"]][0] == "inspiration"


@pytest.mark.unit
def test_face_run6b_owed_prefers_gate_component() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_run6b_j",
		strategy={
			"task_scope": "design_driven",
			"intent": "structural hardcore coordination review",
			"influence_level": "structural",
			"policy_id": "design.greenfield.with_refs.early",
			"right_sizing": {"tier": "initiative"},
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "component_search_plan",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [{"family": "inspiration"}],
				"unpaid": [
					{"family": "component", "suggested": "perception_plan_component_search"},
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
					{"family": "observe", "suggested": "perception_navigate_and_observe"},
				],
			},
		},
	)
	assert face["class"] == "greenfield"
	assert face["owed"][0]["family"] == "component"
	assert face["next"] == "perception_select_component_foundation"


@pytest.mark.unit
def test_face_run6c_policy_reconcile_beats_polluted_fix_intent() -> None:
	"""Run 6c: matters/summary 'observe, fix, verify' must not keep hotfix under greenfield policy."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_run6c_a",
		strategy={
			"task_scope": "design_driven",
			# Polluted the way promote used to fall back to what_matters_now
			"intent": "Resolve: Live UI baseline Minimize scope; observe, fix, verify, ship",
			"influence_level": "structural",
			"policy_id": "design.greenfield.no_refs.early",
			"right_sizing": {"tier": "initiative"},
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "inspiration_workflow",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "component", "suggested": "perception_select_component_foundation"},
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
				],
			},
		},
	)
	assert face["class"] == "greenfield"
	assert face["resource"] == "perception://spine/greenfield"
	assert face["next"] == "perception_inspiration_collect"
	assert "inspiration" in [o["family"] for o in face["owed"]]
	assert face["owed"] != [{"family": "visual_feedback"}] and [
		o["family"] for o in face["owed"]
	] != ["visual_feedback"]


@pytest.mark.unit
def test_face_feature_empty_owed_observes_before_verify() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_feat_empty",
        strategy={
            "task_scope": "feature_incremental",
            "intent": "Add a settings toggle to an existing page",
            "influence_level": "balanced",
            "verification_status": "pending",
            "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
            "episode_portfolio": {"paid": [], "unpaid": []},
        },
    )
    assert face["class"] == "feature"
    assert face["next"] == "perception_navigate_and_observe"
    assert face["claim_ok"] is False


@pytest.mark.unit
def test_face_feature_incremental_not_stolen_by_polish_tier() -> None:
    """Feature scope must stay feature even when right_sizing recommends polish."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
        build_agent_face_card,
    )

    strategy = {
        "task_scope": "feature_incremental",
        "intent": "Add a settings toggle to an existing page",
        "influence_level": "balanced",
        "right_sizing": {"tier": "polish"},
        "verification_status": "pending",
        "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
        "episode_portfolio": {
            "paid": [],
            "unpaid": [{"family": "observe", "suggested": "perception_navigate_and_observe"}],
        },
    }
    assert classify_agent_face(strategy) == "feature"
    face = build_agent_face_card(episode_id="ep_feat_tier", strategy=strategy)
    assert face["class"] == "feature"
    assert face["resource"] == "perception://spine/feature"


@pytest.mark.unit
def test_face_feature_skips_inspiration_owed() -> None:
    """G5: feature class must observe first — not tunnel into inspiration."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_feat",
        strategy={
            "task_scope": "feature_incremental",
            "intent": "Add a settings toggle to the existing page",
            "influence_level": "balanced",
            "verification_status": "pending",
            "implementation_gate": {
                "state": "ready",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [],
                "unpaid": [
                    {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                    {"family": "observe", "suggested": "perception_navigate_and_observe"},
                    {"family": "verify", "suggested": "perception_verify"},
                ],
            },
            "recommended_resource": "perception://guide/feature",
        },
    )
    assert face["class"] == "feature"
    assert face["next"] == "perception_navigate_and_observe"
    assert face["owed"][0]["family"] != "inspiration"
    assert face["resource"] == "perception://spine/feature"


@pytest.mark.unit
def test_face_section_checklist_next_after_verify() -> None:
    """G7: section ceremony routes next to observe and blocks claim."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_sec",
        strategy={
            "task_scope": "design_driven",
            "intent": "Landing page sections",
            "influence_level": "structural",
            "verification_status": "passed",
            "implementation_gate": {
                "state": "ready",
                "prohibited_actions": [],
                "section_checklist_required": True,
            },
            "episode_portfolio": {
                "paid": [{"family": "verify"}],
                "unpaid": [],
            },
        },
    )
    assert "section_checklist" in face["claim_extra"]
    assert face["claim_ok"] is False
    assert face["next"] == "perception_observe"


@pytest.mark.unit
def test_face_spec_revision_next_after_verify() -> None:
    """G8: spec revision routes to snapshot and blocks claim."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_spec",
        strategy={
            "task_scope": "redesign",
            "intent": "Match mockup after draft",
            "influence_level": "structural",
            "verification_status": "passed",
            "spec_revision_gate": {"revision_required": True},
            "implementation_gate": {"state": "ready", "prohibited_actions": []},
            "episode_portfolio": {
                "paid": [{"family": "verify"}, {"family": "snapshot"}],
                "unpaid": [],
            },
        },
    )
    assert "spec_revision" in face["claim_extra"]
    assert face["claim_ok"] is False
    assert face["next"] == "perception_build_design_snapshot"


@pytest.mark.unit
def test_face_plan_component_suggested_remaps_to_select() -> None:
    """G10: unpaid plan_component_search must surface as select with query."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_plan",
        strategy={
            "task_scope": "design_driven",
            "intent": "Build pricing section foundation",
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
    )
    assert face["next"] == "perception_select_component_foundation"
    assert "query" in (face.get("next_args") or {})
    assert not str(face["next_args"]["query"]).startswith("<")


@pytest.mark.unit
def test_face_reference_image_classifies_redesign() -> None:
    """G12: uploaded reference / figma cues → redesign, not greenfield inspiration."""
    from navigation.coordination_intelligence.planning.coordinator_card import (
        classify_agent_face,
        build_agent_face_card,
    )

    strategy = {
        "task_scope": "design_driven",
        "intent": "Match this uploaded reference image to the hero",
        "influence_level": "structural",
        "verification_status": "pending",
        "implementation_gate": {
            "state": "blocked",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_portfolio": {
            "paid": [],
            "unpaid": [
                {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
                {"family": "observe", "suggested": "perception_navigate_and_observe"},
            ],
        },
    }
    assert classify_agent_face(strategy) == "redesign"
    face = build_agent_face_card(episode_id="ep_ref", strategy=strategy)
    assert face["class"] == "redesign"
    assert face["next"] in {
        "perception_navigate_and_observe",
        "perception_build_design_snapshot",
    }
    assert face["next"] != "perception_inspiration_collect"


@pytest.mark.unit
def test_face_claim_ok_false_before_verify() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_nv",
        strategy={
            "task_scope": "hotfix",
            "influence_level": "surgical",
            "verification_status": "pending",
            "implementation_gate": {"state": "maintenance", "prohibited_actions": []},
            "episode_portfolio": {"paid": [], "unpaid": []},
            "recommended_resource": "perception://spine/hotfix",
        },
    )
    assert face["claim_ok"] is False


@pytest.mark.unit
def test_face_forms_ignores_gate_component_when_portfolio_empty() -> None:
	"""Outside design initiative, portfolio unpaid is empty — forms must still probe."""
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_forms",
		strategy={
			"task_scope": "feature_incremental",
			"intent": "Verify the validation form at /forms/validation works",
			"influence_level": "minimal",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "component_search_plan",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {"paid": [], "unpaid": []},
			"recommended_resource": "perception://guide/forms",
		},
	)
	assert face["class"] == "forms"
	assert face["next"] == "perception_probe_form"
	assert face["owed"][0]["family"] == "forms"
	assert face["claim_ok"] is False
	assert "component" not in {o["family"] for o in face["owed"]}


@pytest.mark.unit
def test_face_forms_conflict_prefers_face_card() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_forms_conflict",
		strategy={
			"task_scope": "feature_incremental",
			"intent": "Fix checkout form validation and guards",
			"influence_level": "minimal",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "component_search_plan",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {"paid": [], "unpaid": []},
			"recommended_resource": "perception://spine/forms",
		},
	)
	assert face["class"] == "forms"
	conflict = face.get("conflict") or {}
	assert conflict.get("prefer") == "face.card"
	assert face["next"] == "perception_probe_form"


@pytest.mark.unit
def test_face_hotfix_ignores_gate_inspiration() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_hf",
		strategy={
			"task_scope": "hotfix",
			"intent": "fix overlapping CTA button layout bug",
			"influence_level": "surgical",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "maintenance",
				"next_required_capability": "inspiration_workflow",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "component", "suggested": "perception_select_component_foundation"},
				],
			},
		},
	)
	assert face["class"] == "hotfix"
	assert face["next"] == "perception_navigate_and_observe"
	assert "inspiration" not in {o["family"] for o in face["owed"]}
	assert "component" not in {o["family"] for o in face["owed"]}


@pytest.mark.unit
def test_face_empty_owed_climbs_verify_not_plan_component() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_done_ladder",
		strategy={
			"task_scope": "design_driven",
			"intent": "Build a SaaS landing page",
			"influence_level": "structural",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "ready",
				"next_required_capability": "component_search_plan",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [
					{"family": "inspiration"},
					{"family": "visual_feedback"},
					{"family": "observe"},
					{"family": "component"},
				],
				"unpaid": [],
			},
		},
	)
	assert face["class"] == "greenfield"
	assert face["next"] == "perception_verify"
	assert face["claim_ok"] is False


@pytest.mark.unit
def test_face_redesign_bridges_observe_then_snapshot() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_rd",
		strategy={
			"task_scope": "redesign",
			"intent": "Redesign the dashboard to match the mockup",
			"influence_level": "structural",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "blocked",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "snapshot", "suggested": "perception_build_design_snapshot"},
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
				],
			},
		},
	)
	assert face["class"] == "redesign"
	assert face["next"] == "perception_navigate_and_observe"
	assert face["next_args"].get("then") == "perception_build_design_snapshot"
	# After observe paid, next returns to snapshot
	face2 = build_agent_face_card(
		episode_id="ep_rd2",
		strategy={
			"task_scope": "redesign",
			"intent": "Redesign the dashboard to match the mockup",
			"influence_level": "structural",
			"active_route": "/",
			"verification_status": "pending",
			"implementation_gate": {
				"state": "provisional",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [{"family": "observe"}],
				# Simulate portfolio dropping snapshot after observe — face must re-inject
				"unpaid": [
					{"family": "visual_feedback", "suggested": "perception_visual_feedback"},
					{"family": "component", "suggested": "perception_select_component_foundation"},
				],
			},
		},
	)
	assert face2["next"] == "perception_build_design_snapshot"
	assert face2["owed"][0]["family"] == "snapshot"


@pytest.mark.unit
def test_face_ship_extra_routes_to_design_review() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_ship",
		strategy={
			"task_scope": "design_driven",
			"intent": "Build a SaaS landing page",
			"influence_level": "structural",
			"verification_status": "passed",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": ["claim_complete"],
				"ship_council_required": True,
			},
			"episode_portfolio": {
				"paid": [{"family": "verify"}, {"family": "inspiration"}],
				"unpaid": [],
			},
		},
	)
	assert "ship_council" in face["claim_extra"]
	assert face["next"] == "perception_design_review"
	assert face["next_args"].get("mode") == "ship"
	assert face["claim_ok"] is False


@pytest.mark.unit
def test_face_depth_light_for_hotfix_skips_ship() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_depth_hf",
		strategy={
			"task_scope": "hotfix",
			"intent": "fix overlapping button",
			"influence_level": "surgical",
			"verification_status": "pending",
			"right_sizing": {"tier": "touch_up"},
			"implementation_gate": {"state": "maintenance", "prohibited_actions": ["claim_complete"]},
			"episode_portfolio": {"paid": [], "unpaid": []},
		},
	)
	assert face["depth"] == "light"
	by_id = {row["id"]: row for row in face["finish"]}
	assert by_id["ship_council"]["status"] == "skip"
	assert by_id["section_checklist"]["status"] == "skip"
	assert by_id["verify"]["status"] == "todo"
	assert by_id["claim"]["status"] == "blocked"


@pytest.mark.unit
def test_face_depth_full_for_greenfield_lists_ship() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_depth_gf",
		strategy={
			"task_scope": "design_driven",
			"intent": "Build a SaaS landing page",
			"influence_level": "structural",
			"verification_status": "pending",
			"right_sizing": {"tier": "initiative"},
			"implementation_gate": {
				"state": "blocked",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
				],
			},
		},
	)
	assert face["depth"] == "full"
	by_id = {row["id"]: row for row in face["finish"]}
	assert by_id["inspiration"]["status"] == "todo"
	# Not required by gate → skip (Run 6: do not leave todo forever)
	assert by_id["ship_council"]["status"] == "skip"
	assert by_id["section_checklist"]["status"] == "skip"
	assert by_id["claim"]["status"] == "blocked"


@pytest.mark.unit
def test_face_finish_ship_todo_when_required() -> None:
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_depth_ship",
		strategy={
			"task_scope": "design_driven",
			"intent": "Build a SaaS landing page",
			"influence_level": "structural",
			"verification_status": "passed",
			"right_sizing": {"tier": "initiative"},
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
	)
	by_id = {row["id"]: row for row in face["finish"]}
	assert by_id["ship_council"]["status"] == "todo"
	assert by_id["section_checklist"]["status"] == "skip"


@pytest.mark.unit
def test_face_component_next_includes_query_args() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_c",
        strategy={
            "task_scope": "design_driven",
            "intent": "Build a SaaS landing page with strong CTA",
            "influence_level": "structural",
            "implementation_gate": {
                "state": "blocked",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [{"family": "inspiration"}],
                "unpaid": [
                    {"family": "component", "suggested": "perception_select_component_foundation"},
                    {"family": "visual_feedback", "suggested": "perception_visual_feedback"},
                    {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
                ],
            },
        },
    )
    # Class priority: visual_feedback / snapshot before component for greenfield
    assert face["class"] == "greenfield"
    assert face["owed"][0]["family"] in {"visual_feedback", "snapshot", "inspiration_extract"}
    # When component is next, args must include query
    comp = next((o for o in face["owed"] if o["family"] == "component"), None)
    assert comp is not None
    assert comp["tool"] == "perception_select_component_foundation"
    assert "query" in (comp.get("args") or {})


@pytest.mark.unit
def test_coordinator_card_portfolio_still_works() -> None:
    strategy = {
        "host_action": "BLOCKED: read perception://getting-started",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_confidence": {"score": 0.2, "band": "low"},
        "episode_portfolio": {
            "paid": [{"family": "verify"}],
            "unpaid": [{"family": "inspiration"}, {"family": "snapshot"}],
        },
        "evidence_quality_alerts": ["EVIDENCE THIN: last snapshot advanced"],
        "recommended_resource": "perception://getting-started",
    }
    card = build_coordinator_card(
        episode_id="ep1",
        strategy=strategy,
        suggested_capability="inspiration_workflow",
        suggested_semantic_action="follow_gate:inspiration_workflow",
        stop_reason=None,
    )
    assert card["schema"] == "coordinator_card.v1"
    assert card["episode_id"] == "ep1"
    assert card["integrated"] is True
    assert card["host_action"].startswith("BLOCKED")
    assert card["gate"]["state"] == "blocked"
    assert card["implementation_gate"]["state"] == "blocked"  # alias
    assert "briefing" not in card
    assert "evidence_plan" not in card
    assert card["portfolio"]["paid"] == ["verify"]
    assert card["portfolio"]["unpaid"] == ["inspiration", "snapshot"]
    assert card["evidence_quality_alerts"][0].startswith("EVIDENCE THIN")
    assert card["confidence"]["band"] == "low"


@pytest.mark.unit
def test_strategy_fingerprint_stable_for_same_psm():
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True, "revision_required": False},
    }
    psm.episode.verification_status = "passed"
    a = strategy_fingerprint(psm)
    b = strategy_fingerprint(psm)
    assert a == b
    assert isinstance(a, str) and len(a) >= 8


@pytest.mark.unit
def test_strategy_fingerprint_changes_when_thin_flips() -> None:
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
        "quality": {"thin": True},
    }
    before = strategy_fingerprint(psm)
    psm.evidence.capability_ledger["design_snapshot"]["quality"]["thin"] = False
    after = strategy_fingerprint(psm)
    assert before != after


@pytest.mark.unit
def test_strategy_fingerprint_changes_when_sections_complete() -> None:
    psm = ProjectSituationModel()
    psm.episode.retry_counters["section_checklist"] = {
        "complete": False,
        "sections": [
            {"section_id": "main:0", "observed": True, "verified": False},
        ],
    }
    before = strategy_fingerprint(psm)
    psm.episode.retry_counters["section_checklist"]["complete"] = True
    psm.episode.retry_counters["section_checklist"]["sections"][0]["verified"] = True
    after = strategy_fingerprint(psm)
    assert before != after


@pytest.mark.unit
def test_build_episode_card_adds_what_matters_and_schema() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_episode_card,
    )

    strategy = {
        "host_action": "BLOCKED: gather inspiration",
        "what_matters_now": ["Next (ROI): Bind design reference"],
        "surface_type": "dashboard",
        "influence_level": "structural",
        "implementation_gate": {
            "state": "blocked",
            "next_required_capability": "inspiration_workflow",
            "prohibited_actions": ["claim_complete"],
        },
        "episode_confidence": {"score": 0.1, "band": "low"},
        "episode_portfolio": {"paid": [], "unpaid": [{"family": "inspiration"}]},
        "evidence_quality_alerts": [],
        "recommended_resource": "perception://getting-started",
    }
    card = build_episode_card(episode_id="ep2", strategy=strategy)
    assert card["schema"] == "episode_card.v1"
    assert card["what_matters"].startswith("Next (ROI)")
    assert card["surface_type"] == "dashboard"
    assert card["influence_level"] == "structural"
    assert card["gate"]["state"] == "blocked"
    assert "briefing" not in card


@pytest.mark.unit
def test_enrich_envelope_surfaces_episode_card_on_agent_summary() -> None:
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    from navigation.core.envelope import make_envelope

    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_ep_card",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_build_design_snapshot",
        {"session_id": "sess_ep_card"},
        make_envelope(
            "perception_build_design_snapshot",
            ok=True,
            session_id="sess_ep_card",
            data={"snapshot_id": "s_ep"},
        ),
    )
    card = (out.get("agent_summary") or {}).get("episode_card") or {}
    assert card.get("schema") == "episode_card.v1"
    assert card.get("what_matters")
    assert (out.get("data") or {}).get("episode_card", {}).get("schema") == "episode_card.v1"
    assert (out.get("data") or {}).get("coordinator", {}).get("schema") == "coordinator_card.v1"


@pytest.mark.unit
def test_enrich_envelope_uses_coordinator_card_v1_not_full_briefing() -> None:
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService
    from navigation.core.envelope import make_envelope

    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_card_v1",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    envelope = make_envelope(
        "perception_build_design_snapshot",
        ok=True,
        session_id="sess_card_v1",
        data={"snapshot_id": "thin_card"},
    )
    out = service.on_tool_envelope(
        psm.episode_id,
        "perception_build_design_snapshot",
        {"session_id": "sess_card_v1"},
        envelope,
    )
    card = (out.get("data") or {}).get("coordinator") or {}
    assert card.get("schema") == "coordinator_card.v1"
    assert "briefing" not in card
    assert "evidence_plan" not in card
    assert "psm_summary" not in card
    agent_summary = out.get("agent_summary") or {}
    assert agent_summary.get("engineering_strategy") or (out.get("data") or {}).get(
        "engineering_strategy"
    )


@pytest.mark.unit
def test_compile_skipped_when_fingerprint_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    from navigation.coordination_intelligence import service as service_mod
    from navigation.coordination_intelligence.service import CoordinationIntelligenceService

    calls = {"n": 0}
    real = service_mod.compile_engineering_strategy

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(service_mod, "compile_engineering_strategy", wrapped)
    service = CoordinationIntelligenceService()
    psm = service.episode_start(
        session_id="sess_fp_skip",
        intent="redesign Meridian analytics dashboard",
        lifecycle_stage="S03_design",
        project_maturity="M1",
    )
    psm = service.runtime.require(psm.episode_id)
    first = calls["n"]
    assert first >= 1
    service._compile_engineering_strategy(psm)
    service._compile_engineering_strategy(psm)
    assert calls["n"] == first


@pytest.mark.unit
def test_h02_hotfix_stamp_does_not_steal_greenfield() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_h02",
        strategy={
            "intent": "Build a new product marketing site with distinctive brand from scratch",
            "task_scope": "hotfix",
            "influence_level": "surgical",
            "policy_id": "hotfix.light.surgical",
            "verification_status": "pending",
            "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
            "episode_portfolio": {"paid": [], "unpaid": []},
            "recommended_resource": "perception://getting-started",
        },
    )
    assert face["class"] == "greenfield"
    assert face["evidence_band"] == "very_heavy"
    assert face["next"] == "perception_inspiration_collect"


@pytest.mark.unit
def test_h11_unpaid_inspiration_beats_component_gate() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_h11",
        strategy={
            "intent": "Ship a new product landing with brand-first hero",
            "task_scope": "design_driven",
            "influence_level": "structural",
            "policy_id": "design.greenfield.no_refs.early",
            "verification_status": "pending",
            "implementation_gate": {
                "state": "blocked",
                "next_required_capability": "component_search_plan",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [],
                "unpaid": [
                    {"family": "component", "suggested": "perception_plan_component_search"},
                    {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                ],
            },
            "recommended_resource": "perception://getting-started",
        },
    )
    assert face["class"] == "greenfield"
    assert face["next"] == "perception_inspiration_collect"
    assert face["owed"][0]["family"] == "inspiration"


@pytest.mark.unit
def test_h18_improve_existing_is_feature() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_h18",
        strategy={
            "intent": "Improve the existing marketing page hierarchy and CTA copy",
            "task_scope": "feature_incremental",
            "influence_level": "balanced",
            "policy_id": "design.greenfield.no_refs.early",
            "verification_status": "pending",
            "implementation_gate": {"state": "ready", "prohibited_actions": ["claim_complete"]},
            "episode_portfolio": {"paid": [], "unpaid": []},
            "recommended_resource": "perception://getting-started",
        },
    )
    assert face["class"] == "feature"
    assert face["evidence_band"] == "heavy"
    assert "inspiration" not in [o["family"] for o in face["owed"]]


@pytest.mark.unit
def test_h20_restyle_match_brand_is_redesign() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_h20",
        strategy={
            "intent": "Restyle the settings surface to match the new brand system",
            "task_scope": "design_driven",
            "influence_level": "structural",
            "policy_id": "design.greenfield.no_refs.early",
            "verification_status": "pending",
            "implementation_gate": {"state": "blocked", "prohibited_actions": ["claim_complete"]},
            "episode_portfolio": {
                "paid": [],
                "unpaid": [
                    {"family": "snapshot", "suggested": "perception_build_design_snapshot"},
                    {"family": "observe", "suggested": "perception_navigate_and_observe"},
                    {"family": "inspiration", "suggested": "perception_inspiration_collect"},
                ],
            },
            "recommended_resource": "perception://getting-started",
        },
    )
    assert face["class"] == "redesign"
    assert face["next"] != "perception_inspiration_collect"


@pytest.mark.unit
def test_h21_forms_done_ignores_stale_unpaid_probe() -> None:
    from navigation.coordination_intelligence.planning.coordinator_card import (
        build_agent_face_card,
    )

    face = build_agent_face_card(
        episode_id="ep_h21",
        strategy={
            "intent": "Verify /forms/validation invalid then valid submit",
            "task_scope": "forms",
            "influence_level": "minimal",
            "verification_status": "passed",
            "implementation_gate": {
                "state": "ready",
                "prohibited_actions": ["claim_complete"],
            },
            "episode_portfolio": {
                "paid": [{"family": "forms"}, {"family": "verify"}],
                "unpaid": [{"family": "forms", "suggested": "perception_probe_form"}],
            },
            "recommended_resource": "perception://spine/forms",
        },
    )
    assert face["claim_ok"] is True
    assert face["next"] == ""
    assert face["next"] != "perception_probe_form"
