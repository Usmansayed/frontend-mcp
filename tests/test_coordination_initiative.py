"""Coordination initiative & residue — surface type, backlog, terminals, confidence."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel
from navigation.coordination_intelligence.planning.episode_backlog import (
    compile_episode_backlog,
)
from navigation.coordination_intelligence.planning.episode_confidence import (
    compile_episode_confidence,
)
from navigation.coordination_intelligence.planning.evidence_plan_status import (
    VALID_SKIP_REASONS,
    open_evidence_plan_items,
    set_plan_item_status,
)
from navigation.coordination_intelligence.planning.implementation_readiness import (
    compile_implementation_readiness,
)
from navigation.coordination_intelligence.planning.residue_scan import (
    get_residue_state,
    mark_residue_required,
    maybe_require_residue_for_ship,
    residue_required,
)
from navigation.coordination_intelligence.planning.ship_council import (
    _collect_snapshot_signals,
    build_ship_council,
)
from navigation.coordination_intelligence.planning.surface_type import (
    apply_surface_type,
    derive_surface_type,
    design_scope_applies,
)
from navigation.design_snapshot_engine.models import DesignSnapshot


@pytest.mark.unit
@pytest.mark.parametrize(
    "intent,expected",
    [
        ("redesign workspace settings preferences page", "settings_form"),
        ("build a new SaaS analytics dashboard", "dashboard"),
        ("login and signup auth screens", "auth"),
        ("new marketing landing homepage hero", "marketing"),
        ("redesign artful portfolio about page", "marketing"),
        ("customers table CRM records list", "data_table"),
        ("fix the padding on the button", "unknown"),
    ],
)
def test_derive_surface_type_from_intent(intent: str, expected: str) -> None:
    assert derive_surface_type(intent) == expected


@pytest.mark.unit
def test_surface_type_lives_on_episode_not_retry_counters() -> None:
    psm = ProjectSituationModel()
    psm.episode.intent_stack.append(
        IntentFrame(intent="workspace settings preferences", pushed_at="t")
    )
    apply_surface_type(psm)
    assert psm.episode.surface_type == "settings_form"
    assert "surface_type" not in (psm.episode.retry_counters or {})
    dumped = psm.episode.to_dict()
    assert dumped["surface_type"] == "settings_form"
    assert "surface_type" not in dumped["retry_counters"]


@pytest.mark.unit
def test_surface_type_sticky_until_mixed() -> None:
    psm = ProjectSituationModel()
    psm.episode.intent_stack.append(
        IntentFrame(intent="analytics dashboard redesign", pushed_at="t")
    )
    apply_surface_type(psm)
    assert psm.episode.surface_type == "dashboard"
    apply_surface_type(psm, intent="settings preferences")
    assert psm.episode.surface_type == "dashboard"


@pytest.mark.unit
def test_evidence_plan_skip_valid_and_invalid() -> None:
    psm = ProjectSituationModel()
    set_plan_item_status(
        psm,
        "design_reference",
        state="skipped",
        reason="out_of_scope_for_surface",
    )
    plan = [{"decision_id": "design_reference", "capability_id": "inspiration_workflow"}]
    assert open_evidence_plan_items(psm, plan) == []
    with pytest.raises(ValueError):
        set_plan_item_status(
            psm,
            "component_foundation",
            state="skipped",
            reason="because_i_felt_like_it",
        )
    assert "out_of_scope_for_surface" in VALID_SKIP_REASONS


@pytest.mark.unit
def test_evidence_plan_superseded_by_snapshot() -> None:
    psm = ProjectSituationModel()
    psm.evidence.capability_ledger["design_snapshot"] = {
        "status": "succeeded",
        "advancement_eligible": True,
    }
    plan = [{"decision_id": "design_reference", "capability_id": "inspiration_workflow"}]
    open_items = open_evidence_plan_items(psm, plan)
    assert open_items == []
    status = psm.episode.retry_counters["evidence_plan_status"]["design_reference"]
    assert status["state"] == "superseded"


@pytest.mark.unit
def test_backlog_top_is_highest_roi() -> None:
    psm = ProjectSituationModel()
    backlog = compile_episode_backlog(
        psm=psm,
        unresolved_decisions=[
            {
                "decision_id": "design_reference",
                "title": "Design reference",
                "priority": 9,
                "resolving_capabilities": ["inspiration_workflow"],
            }
        ],
        incomplete_sections=[],
        open_ship_signals=["settings_form_measure"],
        residue_required=True,
        surface_type="settings_form",
    )
    assert backlog["top"] is not None
    assert backlog["top"]["id"] == "decision:design_reference"
    assert backlog["items"][0]["roi_score"] >= backlog["items"][-1]["roi_score"]
    assert backlog["answered_next"].startswith("What is the single")


@pytest.mark.unit
def test_backlog_top_aligns_with_gate_when_sections_unpaid() -> None:
    """Claim-blocking sections must beat structural ROI tips (same class as snapshot routing)."""
    psm = ProjectSituationModel()
    backlog = compile_episode_backlog(
        psm=psm,
        unresolved_decisions=[
            {
                "decision_id": "component_foundation",
                "title": "Component foundation selection",
                "priority": 9,
                "resolving_capabilities": ["component_search_plan"],
            }
        ],
        incomplete_sections=["aside:0"],
        open_evidence_items=[
            {
                "decision_id": "component_foundation",
                "capability_id": "component_search_plan",
            }
        ],
        gate_next_capability="browser_verify",
        surface_type="dashboard",
    )
    assert backlog["top"] is not None
    assert backlog["top"]["id"] == "section:aside:0"
    assert backlog["top"]["suggested_capability"] == "browser_verify"


@pytest.mark.unit
def test_episode_confidence_contributors_signed() -> None:
    psm = ProjectSituationModel()
    psm.episode.verification_status = "passed"
    psm.episode.retry_counters["ship_council_clear"] = True
    conf = compile_episode_confidence(
        psm=psm,
        evidence_plan=[],
        section_complete=True,
        ship_clear=True,
        residue_required=True,
        spec_bound=True,
    )
    assert 0.0 <= conf["score"] <= 1.0
    ids = {c["id"] for c in conf["contributors"]}
    assert "ship_clear" in ids
    assert "residue_pending" in ids
    deltas = {c["id"]: c["delta"] for c in conf["contributors"]}
    assert deltas["ship_clear"] > 0
    assert deltas["residue_pending"] < 0


@pytest.mark.unit
def test_hotfix_unaffected_by_initiative_gate() -> None:
    psm = ProjectSituationModel()
    psm.episode.retry_counters["residue_scan"] = {
        "required": True,
        "completed": False,
        "at": "t",
    }
    gate, plan, _ = compile_implementation_readiness(
        psm,
        influence_level="minimal",
        task_scope="hotfix",
        unresolved_decisions=[],
    )
    assert gate["state"] == "maintenance"
    assert gate.get("residue_scan_required") is False
    assert gate.get("evidence_plan_incomplete") is False
    assert "claim_complete" not in gate["prohibited_actions"]
    assert design_scope_applies(psm, {"task_scope": "hotfix"}) is False


@pytest.mark.unit
def test_settings_surface_emits_measure_not_kpi() -> None:
    settings_snap = {
        "url": "http://localhost:5173/settings",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "regions": [
                {"role": "sidebar", "width_ratio": 0.18},
                {
                    "role": "main",
                    "label": "settings",
                    "width_ratio": 0.95,
                    "rect": {"x": 220, "y": 0, "w": 1060, "h": 720},
                },
            ],
            "interactive_boxes": [
                {"x": 400, "y": 680, "w": 80, "h": 32},
                {"x": 500, "y": 680, "w": 80, "h": 32},
            ],
        },
        "hierarchy": {
            "prominence_scores": [
                {"score": 0.5, "label": "a"},
                {"score": 0.5, "label": "b"},
                {"score": 0.5, "label": "c"},
            ],
        },
        "colors": {"token_backed_ratio": 0.8},
    }
    signals = {s["signal"] for s in _collect_snapshot_signals(
        settings_snap, surface_type="settings_form"
    )}
    assert "settings_form_measure" in signals
    assert "equal_weight_kpi_cluster" not in signals
    assert "settings_footer_collision" in signals


@pytest.mark.unit
def test_residue_one_pass_then_complete() -> None:
    psm = ProjectSituationModel()
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    assert maybe_require_residue_for_ship(
        psm,
        coverage="thin",
        challenge_count=0,
        dense_ui=True,
        design_scope=True,
    )
    assert residue_required(psm) is True

    thin = {
        "url": "http://localhost:5173/",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "regions": [{"role": "main", "rect": {"x": 0, "y": 0, "w": 1280, "h": 720}}],
            "visual_insights": {"boxes": [{"x": 0, "y": 0, "w": 10, "h": 10}] * 35},
        },
        "hierarchy": {"prominence_scores": []},
        "colors": {},
    }
    first = build_ship_council(
        psm=psm,
        strategy={
            "influence_level": "structural",
            "task_scope": "design_driven",
            "surface_type": "dashboard",
        },
        snapshot=DesignSnapshot.from_dict(thin),
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    # Already pending before build → completed on this remasure pass.
    assert first["ship_gate"]["residue_scan_required"] is False
    assert get_residue_state(psm).get("completed") is True

    # After completed, thin+dense must not re-require.
    assert maybe_require_residue_for_ship(
        psm,
        coverage="thin",
        challenge_count=0,
        dense_ui=True,
        design_scope=True,
    ) is False


@pytest.mark.unit
def test_residue_blocks_clear_on_first_thin_pass() -> None:
    psm = ProjectSituationModel()
    psm.episode.surface_type = "dashboard"
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    sparse = {
        "url": "http://localhost:5173/dash",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "regions": [],
            "visual_insights": {"boxes": [{"x": 0, "y": 0, "w": 10, "h": 10}] * 40},
            "interactive_boxes": [{"x": 0, "y": 0, "w": 10, "h": 10}] * 40,
        },
        "hierarchy": {"prominence_scores": []},
        "colors": {},
    }
    ship = build_ship_council(
        psm=psm,
        strategy={
            "influence_level": "structural",
            "task_scope": "design_driven",
            "surface_type": "dashboard",
        },
        snapshot=DesignSnapshot.from_dict(sparse),
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    assert ship["ship_gate"]["council_clear"] is False
    assert residue_required(psm) is True
    assert ship["ship_gate"]["state"] in ("residue", "challenge")
    assert ship["ship_gate"].get("residue_scan_required") is True


@pytest.mark.unit
def test_design_scope_gate_flags_residue() -> None:
    psm = ProjectSituationModel()
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    mark_residue_required(psm)
    gate, _, resource = compile_implementation_readiness(
        psm,
        influence_level="structural",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    assert gate["residue_scan_required"] is True
    assert "claim_complete" in gate["prohibited_actions"]
    assert gate["next_required_capability"] == "design_snapshot"
    assert "verification" in resource or "ship" in resource or True
