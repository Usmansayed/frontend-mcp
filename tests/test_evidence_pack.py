"""Evidence Pack Loop — band × class packs and claim gates."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.coordinator_card import build_agent_face_card
from navigation.coordination_intelligence.planning.evidence_pack import (
	build_evidence_pack,
	pack_implement_blocked,
	resolve_evidence_band,
)
from navigation.coordination_intelligence.planning.right_sizing import (
	recommend_effort_tier,
	tier_to_evidence_band,
)


@pytest.mark.unit
def test_feature_incremental_defaults_to_heavy_band() -> None:
	psm = ProjectSituationModel()
	psm.episode.intent_stack.append(
		IntentFrame(intent="Improve the hero CTA copy on the existing page", pushed_at=_utc_now())
	)
	rec = recommend_effort_tier(psm, task_scope="feature_incremental")
	assert rec["tier"] == "feature"
	assert rec["evidence_band"] == "heavy"
	assert tier_to_evidence_band("feature") == "heavy"


@pytest.mark.unit
def test_explicit_polish_cues_stay_medium() -> None:
	psm = ProjectSituationModel()
	psm.episode.intent_stack.append(
		IntentFrame(intent="Tighten spacing on the navbar only — visual polish", pushed_at=_utc_now())
	)
	rec = recommend_effort_tier(psm, task_scope="feature_incremental")
	assert rec["tier"] == "polish"
	assert rec["evidence_band"] == "medium"


@pytest.mark.unit
def test_hotfix_pack_is_light_no_inspiration() -> None:
	pack = build_evidence_pack(
		face_class="hotfix",
		strategy={"task_scope": "hotfix", "episode_portfolio": {"paid": [], "unpaid": []}},
		band="light",
	)
	assert pack["band"] == "light"
	assert "inspiration" not in pack["phases"]
	assert pack["phases"] == ["observe", "verify"]


@pytest.mark.unit
def test_forms_pack_no_inspiration() -> None:
	pack = build_evidence_pack(
		face_class="forms",
		strategy={"task_scope": "hotfix", "episode_portfolio": {"paid": [], "unpaid": []}},
		band="light",
	)
	assert "inspiration" not in pack["phases"]
	assert "forms" in pack["phases"]


@pytest.mark.unit
def test_greenfield_heavy_pack_has_inspiration_and_component() -> None:
	pack = build_evidence_pack(
		face_class="greenfield",
		strategy={
			"task_scope": "design_driven",
			"episode_portfolio": {"paid": [], "unpaid": []},
		},
		band="heavy",
	)
	assert "inspiration" in pack["phases"]
	assert "component" in pack["phases"]
	assert "inspiration" in pack["critical"]
	assert pack_implement_blocked(face_class="greenfield", pack=pack) is True


@pytest.mark.unit
def test_face_card_emits_band_pack_implement_blocked() -> None:
	face = build_agent_face_card(
		episode_id="ep_pack",
		strategy={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"intent": "Build a new SaaS landing page",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "inspiration_workflow",
				"prohibited_actions": ["claim_complete", "broad_visual_implementation"],
				"ship_council_required": True,
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration", "suggested": "perception_inspiration_collect"},
					{"family": "component", "suggested": "perception_select_component_foundation"},
					{"family": "verify", "suggested": "perception_verify"},
				],
			},
		},
	)
	assert face["class"] == "greenfield"
	assert face["evidence_band"] == "very_heavy"
	assert face["pack"]["id"].startswith("greenfield.")
	assert "inspiration" in face["pack"]["critical"]
	assert face["implement_blocked"] is True
	assert face["claim_ok"] is False
	assert face["owed"][0]["family"] == "inspiration"


@pytest.mark.unit
def test_face_hotfix_band_light_claim_ok_when_verified() -> None:
	face = build_agent_face_card(
		episode_id="ep_hf",
		strategy={
			"task_scope": "hotfix",
			"intent": "Fix overlapping mobile menu button",
			"influence_level": "surgical",
			"verification_status": "passed",
			"implementation_gate": {"state": "ready", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [{"family": "observe"}, {"family": "verify"}],
				"unpaid": [],
			},
		},
	)
	assert face["class"] == "hotfix"
	assert face["evidence_band"] == "light"
	assert "inspiration" not in {o["family"] for o in face["owed"]}
	assert face["claim_ok"] is True
	assert face["implement_blocked"] is False


@pytest.mark.unit
def test_resolve_band_design_driven_very_heavy() -> None:
	assert (
		resolve_evidence_band({"task_scope": "design_driven", "right_sizing": {"tier": "feature"}})
		== "very_heavy"
	)
