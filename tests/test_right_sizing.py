"""AI-centric right-sizing — Evidence Pack Loop bands (default heavy for normal UI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.engineering_strategy import (
    compile_engineering_strategy,
    surface_engineering_strategy,
)
from navigation.coordination_intelligence.planning.implementation_readiness import (
    compile_implementation_readiness,
)
from navigation.coordination_intelligence.planning.right_sizing import (
    RIGHT_SIZING_RESOURCE,
    build_right_sizing_card,
    recommend_effort_tier,
    resolve_effort_tier,
    set_effort_tier,
)
from navigation.coordination_intelligence.planning.ship_council import episode_needs_ship_council
from navigation.coordination_intelligence.planning.surface_type import design_scope_applies
from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.mcp.resources import read_resource


def _navbar_psm(*, verified: bool = True) -> ProjectSituationModel:
    psm = ProjectSituationModel()
    psm.episode.intent_stack.append(
        IntentFrame(intent="improvise the navbar", pushed_at=_utc_now())
    )
    psm.situation.situation_class = "new_feature"
    psm.situation.lifecycle_stage = "S05_implementation"
    psm.artifacts.snapshot_id = "snap_nav"
    if verified:
        psm.episode.verification_status = "passed"
    return psm


@pytest.mark.unit
def test_navbar_incremental_defaults_to_heavy_not_initiative() -> None:
    psm = _navbar_psm()
    rec = recommend_effort_tier(psm, task_scope="feature_incremental", influence_level="balanced")
    assert rec["tier"] == "feature"
    assert rec["evidence_band"] == "heavy"
    assert "inspiration_workflow" in rec["skip"]
    assert "ship_council" in rec.get("skip", []) or "full_greenfield_ladder" in rec["skip"]


@pytest.mark.unit
def test_navbar_heavy_does_not_arm_ship_or_initiative() -> None:
    psm = _navbar_psm()
    strategy = {"task_scope": "feature_incremental", "influence_level": "balanced"}
    assert design_scope_applies(psm, strategy) is False
    assert episode_needs_ship_council(psm, strategy) is False

    gate, _, resource = compile_implementation_readiness(
        psm,
        influence_level="balanced",
        task_scope="feature_incremental",
        unresolved_decisions=[],
    )
    assert gate.get("ship_council_required") is not True
    assert gate.get("section_checklist_required") is not True
    assert gate.get("residue_scan_required") is not True
    assert "claim_complete" not in (gate.get("prohibited_actions") or [])
    assert gate.get("right_sizing", {}).get("tier") == "feature"
    assert resource == RIGHT_SIZING_RESOURCE


@pytest.mark.unit
def test_agent_can_upgrade_heavy_to_initiative() -> None:
    psm = _navbar_psm()
    set_effort_tier(psm, "initiative", source="agent")
    strategy = {"task_scope": "feature_incremental", "influence_level": "balanced"}
    resolved = resolve_effort_tier(psm, strategy)
    assert resolved["tier"] == "initiative"
    assert resolved["declared"] is True
    assert design_scope_applies(psm, strategy) is True
    assert episode_needs_ship_council(psm, strategy) is True

    gate, _, _ = compile_implementation_readiness(
        psm,
        influence_level="balanced",
        task_scope="feature_incremental",
        unresolved_decisions=[],
    )
    assert gate.get("ship_council_required") is True
    assert "claim_complete" in gate["prohibited_actions"]


@pytest.mark.unit
def test_design_driven_still_recommends_initiative() -> None:
    psm = ProjectSituationModel()
    psm.episode.intent_stack.append(
        IntentFrame(intent="build a new SaaS analytics dashboard", pushed_at=_utc_now())
    )
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    rec = recommend_effort_tier(psm, task_scope="design_driven", influence_level="structural")
    assert rec["tier"] == "initiative"
    assert rec["evidence_band"] == "very_heavy"
    assert episode_needs_ship_council(
        psm,
        {"task_scope": "design_driven", "influence_level": "structural"},
    )


@pytest.mark.unit
def test_agent_can_downgrade_sticky_design_to_polish() -> None:
    """Agent judgment wins — sticky design still recommends initiative, override demotes gates."""
    psm = ProjectSituationModel()
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    set_effort_tier(psm, "polish", source="agent")
    strategy = {"task_scope": "design_driven", "influence_level": "balanced"}
    assert resolve_effort_tier(psm, strategy)["tier"] == "polish"
    assert design_scope_applies(psm, strategy) is False
    assert episode_needs_ship_council(psm, strategy) is False


@pytest.mark.unit
def test_strategy_surfaces_right_sizing_on_agent_summary() -> None:
    psm = _navbar_psm(verified=False)
    catalog = load_runtime_artifacts().situation_policy_catalog
    strategy = compile_engineering_strategy(psm, catalog).to_dict()
    assert strategy.get("right_sizing", {}).get("tier") == "feature"
    assert strategy.get("right_sizing", {}).get("evidence_band") == "heavy"

    envelope: dict = {"ok": True, "data": {}}
    surface_engineering_strategy(envelope, strategy, episode_id="ep_test")
    assert envelope["agent_summary"]["right_sizing"]["tier"] == "feature"


@pytest.mark.unit
def test_right_sizing_guide_resource_exists() -> None:
    mime, text, is_blob = read_resource(RIGHT_SIZING_RESOURCE)
    assert mime == "text/markdown"
    assert is_blob is False
    assert "Blast radius" in text
    assert "effort_tier" in text
    assert "polish" in text.lower()


@pytest.mark.unit
def test_build_right_sizing_card_override_hint() -> None:
    psm = _navbar_psm()
    card = build_right_sizing_card(
        psm,
        {"task_scope": "feature_incremental", "influence_level": "balanced"},
    )
    assert card["resource"] == RIGHT_SIZING_RESOURCE
    assert "effort_tier" in card["override_hint"]
    assert card.get("evidence_band") == "heavy"
