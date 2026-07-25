"""EXP-020 evidence-quality baseline promotion + inspiration soft host."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E20 = ROOT / "evals/decision_lab/experiments/EXP-020-evidence-baseline/scenarios"


@pytest.mark.unit
def test_exp020_inspiration_soft_host() -> None:
    r = run_scenario(E20 / "inspiration_soft_host.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp020_baseline_includes_evidence_quality() -> None:
    pack = run_pack()  # default → baseline
    assert pack.pack_id == "baseline"
    assert len(pack.results) >= 25
    assert pack.pass_count == len(pack.results)
    assert pack.passed, pack.scorecard()
    ids = {r.id for r in pack.results}
    assert "exp017_snapshot_quality_payload" in ids
    assert "exp018_host_surfaces_thin_snapshot" in ids
    assert "exp018_host_surfaces_thin_clear_ship" in ids
    assert "exp019_specdiff_soft_seed_honesty" in ids
    assert "exp020_inspiration_soft_host" in ids
