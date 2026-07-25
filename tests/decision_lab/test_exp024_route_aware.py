"""EXP-024 route-aware Meridian."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E24 = ROOT / "evals/decision_lab/experiments/EXP-024-route-aware-meridian/scenarios"


@pytest.mark.unit
def test_exp024_meridian_route_aware_ship() -> None:
    r = run_scenario(E24 / "meridian_route_aware_ship.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp024_baseline_includes_route_aware() -> None:
    pack = run_pack()
    assert pack.pack_id == "baseline"
    assert len(pack.results) >= 25
    assert pack.passed, pack.scorecard()
    assert "exp024_meridian_route_aware_ship" in {r.id for r in pack.results}
