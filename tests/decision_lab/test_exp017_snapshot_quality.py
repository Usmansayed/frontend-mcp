"""EXP-017 snapshot quality enrichment."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.coordination_intelligence.lab.runner import run_scenario
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.psm.normalize import apply_envelope

E17 = ROOT / "evals/decision_lab/experiments/EXP-017-snapshot-quality/scenarios"


@pytest.mark.unit
def test_exp017_snapshot_quality_payload() -> None:
    r = run_scenario(E17 / "snapshot_quality_payload.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_normalize_snapshot_quality_nonempty_and_advances() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_build_design_snapshot",
            "data": {
                "snapshot_id": "s1",
                "snapshot_summary": {
                    "layout_issues": 1,
                    "interactive_count": 9,
                    "wcag_failures": 0,
                    "degraded": ["fonts"],
                },
                "layout": {"regions": [{"role": "main"}, {"role": "aside"}]},
            },
        },
        bundle,
    )
    outcome = psm.evidence.capability_ledger["design_snapshot"]
    assert outcome["status"] == "succeeded"
    assert outcome["advancement_eligible"] is True
    q = outcome["quality"]
    assert q["region_count"] == 2
    assert q["layout_issues"] == 1
    assert q["interactive_count"] == 9
    assert q["degraded_count"] == 1
    assert q["thin"] is False
    assert q["evidence_useful"] is False  # degraded present


@pytest.mark.unit
def test_normalize_inspiration_quality_profiles() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_inspiration_collect",
            "data": {
                "inspiration_collection": {
                    "hits": [
                        {"inspiration_blob": "b1", "profile": {"mood": "calm"}},
                        {"inspiration_blob": "b2"},
                        {"inspiration_blob": "b3", "extracted_profile": {"density": "sparse"}},
                    ]
                },
                "engineering_spec": {"unresolved_by_impact": ["hierarchy", "spacing"]},
                "reference_bind": {"implementation_ready": True, "quality": "seed"},
            },
        },
        bundle,
    )
    q = psm.evidence.capability_ledger["inspiration_workflow"]["quality"]
    assert q["usable_image_refs"] == 3
    assert q["profiles_extracted"] == 2
    assert q["seed_unresolved_count"] == 2
    assert q["implementation_ready"] is True
    assert q["reference_bind_quality"] == "seed"


@pytest.mark.unit
def test_normalize_ship_quality_thin_clear() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_design_review",
            "data": {
                "mode": "ship",
                "challenges": [],
                "ship_gate": {
                    "council_clear": True,
                    "open_high_roi": 0,
                    "coverage": "thin",
                    "coverage_checks": {"regions": False},
                    "surface_type": "dashboard",
                },
            },
        },
        bundle,
    )
    outcome = psm.evidence.capability_ledger["design_review"]
    assert outcome["status"] == "succeeded"
    q = outcome["quality"]
    assert q["thin_clear"] is True
    assert q["coverage"] == "thin"
    assert q["coverage_checks"] == {"regions": False}
