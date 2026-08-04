# tests/test_creative_kit_resources.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.unit
def test_creative_kit_categories_cover_core_atmosphere():
	from navigation.coordination_intelligence.planning.episode_prefetch import (
		_creative_kit_categories,
	)

	cats = [c.value for c in _creative_kit_categories("build a branded landing page")]
	assert "font" in cats
	assert "pattern" in cats
	assert "gradient" in cats
	assert "icon" in cats
	assert "illustration" in cats
	assert "animation" in cats


@pytest.mark.unit
def test_creative_kit_animation_intent():
	from navigation.coordination_intelligence.planning.episode_prefetch import (
		_creative_kit_categories,
	)

	cats = [c.value for c in _creative_kit_categories("add lottie micro animation")]
	assert "animation" in cats


@pytest.mark.unit
def test_greenfield_pack_includes_optional_resources():
	from navigation.coordination_intelligence.planning.evidence_pack import (
		build_evidence_pack,
	)

	pack = build_evidence_pack(
		face_class="greenfield",
		band="very_heavy",
		strategy={
			"task_scope": "design_driven",
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration"},
					{"family": "resources", "suggested": "perception_creative_assets"},
				],
			},
			"implementation_gate": {"state": "blocked"},
		},
	)
	assert "resources" in pack["phases"] or "resources" in pack["remaining"]
	assert "resources" not in pack["critical"]


@pytest.mark.unit
def test_face_card_surfaces_creative_kit_nudge():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_kit",
		strategy={
			"task_scope": "design_driven",
			"intent": "Build a distinctive SaaS landing page",
			"influence_level": "structural",
			"implementation_gate": {
				"state": "blocked",
				"next_required_capability": "inspiration_workflow",
				"prohibited_actions": ["claim_complete"],
			},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration"},
					{"family": "resources", "suggested": "perception_creative_assets"},
				],
			},
		},
	)
	assert face["class"] == "greenfield"
	kit = face.get("creative_kit") or {}
	assert kit.get("tool") == "perception_creative_assets"
	assert "font" in (kit.get("categories") or [])
	owed_fams = [o["family"] for o in face.get("owed") or []]
	# resources is lower priority than inspiration — may appear once top families shift
	assert "inspiration" in owed_fams or face.get("next") == "perception_inspiration_collect"


@pytest.mark.unit
def test_hotfix_excludes_resources_owed():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_hf",
		strategy={
			"task_scope": "hotfix",
			"intent": "fix overlapping mobile menu button",
			"influence_level": "surgical",
			"implementation_gate": {"state": "ready", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "observe"},
					{"family": "resources", "suggested": "perception_creative_assets"},
				],
			},
		},
	)
	assert face["class"] == "hotfix"
	assert "resources" not in [o["family"] for o in face.get("owed") or []]
