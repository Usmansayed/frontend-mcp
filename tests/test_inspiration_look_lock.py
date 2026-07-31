# tests/test_inspiration_look_lock.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.inspiration_look_lock import (
	evaluate_inspiration_look_lock,
	min_primary_refs,
)


@pytest.mark.unit
def test_soft_mood_borrow_alone_does_not_lock():
	out = evaluate_inspiration_look_lock(
		{
			"borrow": ["calm airy navy"],
			"look_lock": {"type_mood": "modern"},
		},
		usable_image_refs=16,
	)
	assert out["look_locked"] is False
	assert out["min_primary_refs"] == 5
	assert any("primary_ref_ids" in r for r in out["reasons"])


@pytest.mark.unit
def test_structured_multi_ref_look_locks():
	refs = [f"web_og:maze.co:{i}" for i in range(5)]
	borrow = [
		{"ref_id": refs[0], "section": "sidebar", "idea": "compact history + New chat"},
		{"ref_id": refs[1], "section": "header", "idea": "thin brand bar"},
		{"ref_id": refs[2], "section": "composer", "idea": "glass rounded input"},
		{"ref_id": refs[3], "section": "thread", "idea": "tight user bubbles"},
		{"ref_id": refs[4], "section": "empty", "idea": "left-biased prompts"},
	]
	out = evaluate_inspiration_look_lock(
		{
			"primary_ref_ids": refs,
			"borrow": borrow,
			"look_lock": {"chrome": "workspace", "composition": "sidebar+thread"},
		},
		usable_image_refs=16,
		evidence_band="very_heavy",
	)
	assert out["look_locked"] is True
	assert out["primary_ref_count"] == 5


@pytest.mark.unit
def test_min_primary_scales_with_wide_hunt():
	assert min_primary_refs(usable_image_refs=16, evidence_band="heavy") == 5
	assert min_primary_refs(usable_image_refs=4, evidence_band="heavy") == 3
	assert min_primary_refs(usable_image_refs=2, evidence_band="heavy") == 2


@pytest.mark.unit
def test_claim_blocked_while_extract_unpaid():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_extract",
		strategy={
			"task_scope": "redesign",
			"intent": "redesign chat UI modern not ChatGPT",
			"influence_level": "structural",
			"verification_status": "passed",
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": [],
				"ship_council_required": False,
				"section_checklist_required": False,
			},
			"episode_portfolio": {
				"paid": [
					{"family": "inspiration"},
					{"family": "observe"},
					{"family": "snapshot"},
					{"family": "visual_feedback"},
					{"family": "verify"},
				],
				"unpaid": [
					{
						"family": "inspiration_extract",
						"reason": "refs collected — LOOK",
						"suggested": "perception_visual_feedback",
					}
				],
			},
			"recommended_resource": "perception://spine/redesign",
		},
	)
	assert face["claim_ok"] is False
