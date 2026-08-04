# tests/test_chrome_fidelity.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.chrome_fidelity import (
	evaluate_chrome_fidelity,
)
from navigation.coordination_intelligence.planning.evidence_pack import (
	CLAIM_STICKY_AFTER_VERIFY,
	PARALLEL_INTEL_FAMILIES,
	build_evidence_pack,
)


@pytest.mark.unit
def test_soft_ok_without_zones_does_not_lock():
	out = evaluate_chrome_fidelity({"judgment": "ok", "notes": "looks modern"})
	assert out["fidelity_locked"] is False
	assert any("missing zones" in r for r in out["reasons"])


@pytest.mark.unit
def test_eighty_percent_zone_scores_lock():
	out = evaluate_chrome_fidelity(
		{
			"chrome_fidelity": [
				{"zone": "nav", "fidelity": 88, "ref_id": "web_og:maze.co:0"},
				{"zone": "aside", "fidelity": 85, "ref_id": "web_og:maze.co:0"},
				{"zone": "main", "fidelity": 82, "ref_id": "web_og:linear.app:1"},
				{"zone": "composer", "fidelity": 90, "ref_id": "web_og:claude.ai:2", "notes": "pill tweak"},
			]
		}
	)
	assert out["fidelity_locked"] is True
	assert out["mean_fidelity"] >= 80


@pytest.mark.unit
def test_weak_sidebar_blocks_lock():
	out = evaluate_chrome_fidelity(
		{
			"fidelity_zones": {
				"header": 90,
				"sidebar": 40,
				"thread": 85,
				"input": 88,
			}
		}
	)
	assert out["fidelity_locked"] is False
	assert any("aside" in r or "below" in r for r in out["reasons"])


@pytest.mark.unit
def test_greenfield_heavy_pack_critical_includes_copy_intel():
	pack = build_evidence_pack(
		face_class="greenfield",
		strategy={
			"task_scope": "design_driven",
			"right_sizing": {"evidence_band": "heavy", "declared": True},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "resources"},
					{"family": "consistency"},
					{"family": "fidelity"},
					{"family": "component"},
				],
			},
		},
		band="heavy",
	)
	for fam in ("component", "resources", "consistency", "fidelity"):
		assert fam in pack["phases"], fam
		assert fam in pack["critical"], fam
		assert fam in pack["critical_unpaid"], fam


@pytest.mark.unit
def test_claim_blocked_while_fidelity_unpaid_after_verify():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_fidelity",
		strategy={
			"task_scope": "redesign",
			"intent": "redesign chat UI modern",
			"influence_level": "structural",
			"verification_status": "passed",
			"right_sizing": {"evidence_band": "very_heavy", "declared": True},
			"implementation_gate": {
				"state": "ready",
				"prohibited_actions": [],
				"ship_council_required": False,
				"section_checklist_required": False,
			},
			"episode_portfolio": {
				"paid": [
					{"family": "inspiration"},
					{"family": "inspiration_extract"},
					{"family": "observe"},
					{"family": "snapshot"},
					{"family": "visual_feedback"},
					{"family": "component"},
					{"family": "resources"},
					{"family": "consistency"},
					{"family": "verify"},
				],
				"unpaid": [
					{
						"family": "fidelity",
						"reason": "chrome fidelity unpaid",
						"suggested": "perception_visual_feedback",
					}
				],
			},
			"recommended_resource": "perception://spine/redesign",
		},
	)
	assert face["claim_ok"] is False
	assert "resources" in CLAIM_STICKY_AFTER_VERIFY
	assert "consistency" in PARALLEL_INTEL_FAMILIES


@pytest.mark.unit
def test_face_exposes_parallel_batch_on_design_heavy():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_parallel",
		strategy={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"right_sizing": {"evidence_band": "heavy", "declared": True},
			"implementation_gate": {"state": "blocked", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [
					{"family": "inspiration"},
					{"family": "component"},
					{"family": "resources"},
					{"family": "consistency"},
				],
			},
			"recommended_resource": "perception://spine/greenfield",
		},
	)
	can = set(face.get("can_parallel") or [])
	assert "resources" in can or "component" in can or "inspiration" in can
	batch = face.get("parallel_batch") or {}
	assert batch.get("families")
