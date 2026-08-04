"""EXP-019 SpecDiff revision / soft-seed honesty."""
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

E19 = ROOT / "evals/decision_lab/experiments/EXP-019-specdiff-honesty/scenarios"


@pytest.mark.unit
def test_exp019_specdiff_revision_host() -> None:
    r = run_scenario(E19 / "specdiff_revision_host.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp019_specdiff_soft_seed_honesty() -> None:
    r = run_scenario(E19 / "specdiff_soft_seed_honesty.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_normalize_specdiff_quality_on_review() -> None:
    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "ok": True,
            "tool": "perception_design_review",
            "data": {
                "mode": "review",
                "passed": True,
                "engineering_delta": {
                    "top_by_impact": [
                        {
                            "decision_id": "chrome",
                            "severity": "blocking",
                            "from_value": "sticky",
                            "to_value": "static",
                        }
                    ],
                    "items": [
                        {
                            "decision_id": "chrome",
                            "severity": "blocking",
                            "kind": "value_drift",
                            "from_value": "sticky",
                            "to_value": "static",
                        }
                    ],
                },
                "spec_revision_gate": {
                    "reference_bound": True,
                    "evaluated": True,
                    "revision_required": True,
                    "passed": False,
                    "blocking_drifts": [{"decision_id": "chrome"}],
                    "major_drifts": [],
                },
            },
        },
        bundle,
    )
    q = psm.evidence.capability_ledger["design_review"]["quality"]
    assert q["revision_required"] is True
    assert q["delta_top_ids"] == ["chrome"]
    assert q["blocking_drift_count"] == 1
    assert q["soft_seed_partial"] is False
    # Honesty only — still advances when passed=true and transport ok
    assert psm.evidence.capability_ledger["design_review"]["status"] == "succeeded"
