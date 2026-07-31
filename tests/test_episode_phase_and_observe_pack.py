# tests/test_episode_phase_and_observe_pack.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.unit
def test_resolve_episode_phase_greenfield_layout():
	from navigation.coordination_intelligence.planning.episode_phase import (
		resolve_episode_phase,
	)

	info = resolve_episode_phase(
		face_class="greenfield",
		strategy={
			"verification_status": "pending",
			"episode_portfolio": {
				"unpaid": [{"family": "inspiration"}, {"family": "verify"}],
			},
		},
		owed=[{"family": "inspiration"}],
		pack={"remaining": ["inspiration", "verify"]},
	)
	assert info["phase"] == "layout"
	assert "inspiration" in info["hint"].lower() or "Direction" in info["hint"]


@pytest.mark.unit
def test_resolve_episode_phase_forms_flow():
	from navigation.coordination_intelligence.planning.episode_phase import (
		resolve_episode_phase,
	)

	info = resolve_episode_phase(
		face_class="forms",
		strategy={"verification_status": "pending"},
		owed=[{"family": "forms"}],
	)
	assert info["phase"] == "flow"


@pytest.mark.unit
def test_resolve_episode_phase_ship_when_claim_ok():
	from navigation.coordination_intelligence.planning.episode_phase import (
		resolve_episode_phase,
	)

	info = resolve_episode_phase(
		face_class="hotfix",
		strategy={"verification_status": "passed"},
		owed=[],
		claim_extra=[],
		claim_ok=True,
	)
	assert info["phase"] == "ship"


@pytest.mark.unit
def test_face_card_surfaces_phase():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	face = build_agent_face_card(
		episode_id="ep_phase",
		strategy={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"implementation_gate": {"state": "blocked", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [{"family": "inspiration"}],
			},
			"recommended_resource": "perception://spine/greenfield",
		},
	)
	assert face.get("phase") == "layout"
	assert isinstance(face.get("phase_hint"), str)
	assert face["phase_hint"]


@pytest.mark.unit
def test_resolve_observe_pack_defaults_viewport():
	from navigation.mcp.handlers import _resolve_observe_pack

	assert _resolve_observe_pack({}) == "viewport"
	assert _resolve_observe_pack({"screenshot_pack": "auto"}) == "viewport"
	assert _resolve_observe_pack({"screenshot_pack": "design"}) == "design"
	assert _resolve_observe_pack({"multi_view": True}) == "design"
	assert _resolve_observe_pack({"focus_sections": ["header"]}) == "section"
	assert _resolve_observe_pack({"screenshot_mode": "full"}) == "full"
	assert _resolve_observe_pack({"no_images": True}) == "none"
	assert _resolve_observe_pack({"detail": "metadata_only"}) == "none"


@pytest.mark.unit
def test_resolve_observe_pack_auto_upgrades_for_design_face():
	from navigation.mcp.handlers import _resolve_observe_pack

	assert (
		_resolve_observe_pack({"screenshot_pack": "auto", "face_class": "greenfield"})
		== "design"
	)
	assert (
		_resolve_observe_pack({"screenshot_pack": "auto", "face_class": "redesign"})
		== "design"
	)
	assert (
		_resolve_observe_pack({"screenshot_pack": "auto", "face_class": "hotfix"})
		== "viewport"
	)
	assert (
		_resolve_observe_pack({"screenshot_pack": "auto", "face_class": "forms"})
		== "viewport"
	)
