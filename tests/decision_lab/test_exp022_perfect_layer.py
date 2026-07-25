"""EXP-022 Perfect Layer Phase A lab lock."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E22 = ROOT / "evals/decision_lab/experiments/EXP-022-perfect-layer-phase-a/scenarios"


@pytest.mark.unit
def test_exp022_fingerprint_skip_preserves_host() -> None:
    r = run_scenario(E22 / "slim_coordinator_card.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp022_baseline_includes_perfect_layer() -> None:
    pack = run_pack()
    assert pack.pack_id == "baseline"
    assert len(pack.results) >= 25
    assert pack.passed, pack.scorecard()
    ids = {r.id for r in pack.results}
    assert "exp022_fingerprint_skip_preserves_host" in ids
