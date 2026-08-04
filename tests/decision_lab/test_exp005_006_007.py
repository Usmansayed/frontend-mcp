"""EXP-005 / 006 / 007 session tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

E5 = ROOT / "evals/decision_lab/experiments/EXP-005-meridian-multiroute/scenarios"
E6 = ROOT / "evals/decision_lab/experiments/EXP-006-sections-ship-portfolio/scenarios"
E7 = ROOT / "evals/decision_lab/experiments/EXP-007-confidence-portfolio/scenarios"


@pytest.mark.unit
def test_exp005_meridian_multiroute() -> None:
    r = run_scenario(E5 / "meridian_multiroute.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp006_sections_then_ship() -> None:
    r = run_scenario(E6 / "sections_then_ship.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp007_confidence_after_paid() -> None:
    r = run_scenario(E7 / "confidence_after_paid.yaml")
    assert r.passed, r.failures
    conf = r.final_snapshot.get("episode_confidence") or {}
    ids = {c["id"] for c in conf.get("contributors") or []}
    assert "portfolio_paid" in ids
