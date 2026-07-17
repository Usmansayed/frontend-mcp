"""Strict section checklist + verify-status gating tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.engineering_strategy import (
    compile_engineering_strategy,
)
from navigation.coordination_intelligence.planning.implementation_readiness import (
    compile_implementation_readiness,
)
from navigation.coordination_intelligence.planning.section_checklist import (
    build_section_verify_assertions,
    episode_needs_section_checklist,
    incomplete_sections,
    mark_section_observed,
    mark_section_verified,
    seed_section_checklist_from_regions,
    section_checklist_complete,
)
from navigation.coordination_intelligence.psm.normalize import apply_envelope


@pytest.mark.unit
def test_normalize_sets_verification_from_data_verified_not_transport_ok() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {"verified": False, "reasons": ["url missing /dashboard"]},
        },
        bundle,
    )
    assert psm.episode.verification_status == "failed"

    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {"verified": True, "reasons": []},
        },
        bundle,
    )
    assert psm.episode.verification_status == "passed"


@pytest.mark.unit
def test_page_verify_without_section_id_does_not_close_section() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "rect": {"w": 200, "h": 800}},
            {"role": "main", "rect": {"w": 900, "h": 800}},
        ],
    )
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {"verified": True, "reasons": []},
        },
        bundle,
    )
    assert psm.episode.verification_status == "passed"
    assert incomplete_sections(psm)
    assert not section_checklist_complete(psm.episode.retry_counters["section_checklist"])


@pytest.mark.unit
def test_section_id_verify_closes_only_that_section() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "rect": {"w": 200, "h": 800}},
            {"role": "main", "rect": {"w": 900, "h": 800}},
        ],
    )
    sid = psm.episode.retry_counters["section_checklist"]["sections"][0]["section_id"]
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_observe",
            "data": {"section_id": sid, "scan_id": "scan_1"},
        },
        bundle,
    )
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_verify",
            "data": {"verified": True, "section_id": sid},
        },
        bundle,
    )
    checklist = psm.episode.retry_counters["section_checklist"]
    target = next(s for s in checklist["sections"] if s["section_id"] == sid)
    assert target["observed"] is True
    assert target["verified"] is True
    assert incomplete_sections(psm)
    assert episode_needs_section_checklist(
        psm,
        {"influence_level": "balanced", "task_scope": "design_driven"},
    )


@pytest.mark.unit
def test_seed_section_checklist_from_dashboard_regions() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    regions = [
        {"role": "aside", "label": "nav", "rect": {"x": 0, "y": 0, "w": 240, "h": 800}},
        {"role": "main", "label": "content", "rect": {"x": 240, "y": 0, "w": 1000, "h": 800}},
        {"role": "header", "rect": {"x": 240, "y": 0, "w": 1000, "h": 56}},
        {"role": "section", "text": "KPIs", "rect": {"x": 240, "y": 80, "w": 1000, "h": 120}},
        {"role": "section", "text": "Table", "rect": {"x": 240, "y": 400, "w": 1000, "h": 300}},
        {"role": "footer", "rect": {"x": 240, "y": 760, "w": 1000, "h": 40}},
    ]
    checklist = seed_section_checklist_from_regions(psm, regions)
    assert checklist["required"] is True
    assert 3 <= len(checklist["sections"]) <= 5
    assert not section_checklist_complete(checklist)
    assert episode_needs_section_checklist(
        psm,
        {"influence_level": "balanced", "task_scope": "design_driven"},
    )
    for section in checklist["sections"]:
        asserts = build_section_verify_assertions(section)
        assert asserts
        assert "getBoundingClientRect" in asserts[0]


@pytest.mark.unit
def test_claim_complete_blocked_until_each_section_observed_and_verified() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    psm.episode.intent_stack = [
        IntentFrame(intent="build a new SaaS analytics dashboard", pushed_at=_utc_now()),
    ]
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "rect": {"w": 200, "h": 800}},
            {"role": "main", "rect": {"w": 900, "h": 800}},
            {"role": "header", "rect": {"w": 900, "h": 48}},
        ],
    )
    gate, _, resource = compile_implementation_readiness(
        psm,
        influence_level="balanced",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    assert gate.get("section_checklist_required") is True
    assert "claim_complete" in gate["prohibited_actions"]
    assert incomplete_sections(psm)
    assert "section" in (gate.get("completion_criteria") or "").lower() or resource

    for sid in [s["section_id"] for s in psm.episode.retry_counters["section_checklist"]["sections"]]:
        mark_section_observed(psm, section_id=sid)
        mark_section_verified(psm, section_id=sid, verified=True)

    assert section_checklist_complete(psm.episode.retry_counters["section_checklist"])
    assert episode_needs_section_checklist(
        psm,
        {"influence_level": "balanced", "task_scope": "design_driven"},
    ) is False

    gate2, _, _ = compile_implementation_readiness(
        psm,
        influence_level="balanced",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    # Ship may still be required — claim_complete can remain prohibited for ship.
    assert gate2.get("section_checklist_required") is not True
    assert gate2.get("ship_council_required") is True
    assert "claim_complete" in gate2["prohibited_actions"]


@pytest.mark.unit
def test_strategy_host_action_section_gate_before_ship() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    psm.episode.intent_stack = [
        IntentFrame(intent="build a new SaaS analytics dashboard", pushed_at=_utc_now()),
    ]
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "rect": {"w": 200, "h": 800}},
            {"role": "main", "rect": {"w": 900, "h": 800}},
        ],
    )
    catalog = load_runtime_artifacts().situation_policy_catalog
    strategy = compile_engineering_strategy(psm, catalog).to_dict()
    assert strategy["implementation_gate"]["section_checklist_required"] is True
    assert "SECTION CHECKLIST" in strategy["host_action"]
    assert not any("verify_passed_sufficient" in s for s in strategy.get("stop_conditions") or [])


@pytest.mark.unit
def test_hotfix_skips_section_checklist() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    seed_section_checklist_from_regions(
        psm,
        [{"role": "main", "rect": {"w": 900, "h": 800}}],
    )
    assert episode_needs_section_checklist(
        psm,
        {"influence_level": "minimal", "task_scope": "hotfix"},
    ) is False
    gate, _, _ = compile_implementation_readiness(
        psm,
        influence_level="minimal",
        task_scope="hotfix",
        unresolved_decisions=[],
    )
    assert gate.get("section_checklist_required") is not True
    assert gate.get("ship_council_required") is not True


@pytest.mark.unit
def test_unseeded_checklist_does_not_block_ship_gate() -> None:
    """Ship still required when snapshot exists but sections not seeded yet."""
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    psm.episode.verification_status = "passed"
    gate, _, _ = compile_implementation_readiness(
        psm,
        influence_level="maintenance",
        task_scope="design_driven",
        unresolved_decisions=[],
    )
    assert gate.get("section_checklist_required") is not True
    assert gate.get("ship_council_required") is True
    assert "claim_complete" in gate["prohibited_actions"]
