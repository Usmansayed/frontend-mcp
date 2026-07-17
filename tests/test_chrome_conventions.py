"""Objective chrome convention asserts for perception_verify."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.chrome_conventions import (
    CHROME_PERMANENCE_ASSERTION,
    HORIZONTAL_OVERFLOW_ASSERTION,
    build_chrome_convention_assertions,
    episode_applies_chrome_conventions,
)
from navigation.coordination_intelligence.planning.section_checklist import (
    build_section_verify_assertions,
    seed_section_checklist_from_regions,
)
from navigation.coordination_intelligence.planning.ship_council import build_ship_council
from navigation.design_snapshot_engine.models import DesignSnapshot


@pytest.mark.unit
def test_aside_section_assertions_include_chrome_permanence() -> None:
    asserts = build_section_verify_assertions({"role": "aside", "section_id": "aside:0"})
    assert any("getBoundingClientRect" in a for a in asserts)
    assert any("scrollTo" in a for a in asserts)
    assert CHROME_PERMANENCE_ASSERTION in asserts


@pytest.mark.unit
def test_main_section_assertions_skip_chrome_permanence() -> None:
    asserts = build_section_verify_assertions({"role": "main", "section_id": "main:0"})
    assert CHROME_PERMANENCE_ASSERTION not in asserts


@pytest.mark.unit
def test_design_episode_page_verify_gets_permanence_and_overflow() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_dash"
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    seed_section_checklist_from_regions(
        psm,
        [
            {"role": "aside", "label": "sidebar", "rect": {"w": 220, "h": 800}},
            {"role": "main", "rect": {"w": 1000, "h": 800}},
        ],
    )
    assert episode_applies_chrome_conventions(psm, {"task_scope": "design_driven"})
    asserts = build_chrome_convention_assertions(
        psm,
        section=None,
        strategy={"task_scope": "design_driven"},
    )
    assert CHROME_PERMANENCE_ASSERTION in asserts
    assert HORIZONTAL_OVERFLOW_ASSERTION in asserts


@pytest.mark.unit
def test_hotfix_skips_chrome_conventions() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_x"
    asserts = build_chrome_convention_assertions(
        psm,
        strategy={"task_scope": "hotfix", "influence_level": "minimal"},
    )
    assert asserts == []


@pytest.mark.unit
def test_ship_council_does_not_emit_sticky_or_overflow_conventions() -> None:
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap"
    psm.episode.verification_status = "passed"
    psm.episode.retry_counters["episode_design_scope"] = "design_driven"
    snap = DesignSnapshot.from_dict({
        "url": "http://localhost/dashboard",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "overflow_issues": [{"kind": "horizontal_overflow"}],
            "visual_insights": {"blocking": ["horizontal_overflow"], "issues": []},
            "regions": [
                {"role": "sidebar", "position": "static", "width_ratio": 0.2},
                {"role": "main", "centered": True, "width_ratio": 0.55},
                {"role": "section"},
                {"role": "section"},
                {"role": "section"},
                {"role": "section"},
            ],
        },
        "hierarchy": {
            "prominence_scores": [
                {"score": 0.5},
                {"score": 0.5},
                {"score": 0.5},
            ],
        },
        "colors": {"token_backed_ratio": 0.2},
    })
    ship = build_ship_council(
        psm=psm,
        strategy={"influence_level": "structural", "task_scope": "design_driven"},
        snapshot=snap,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    signals = {c["signal"] for c in ship["challenges"]}
    assert "nav_not_sticky" not in signals
    assert "responsive_breakage" not in signals
    assert "narrow_centered_main" in signals or "equal_weight_kpi_cluster" in signals or "theme_not_coupled" in signals
