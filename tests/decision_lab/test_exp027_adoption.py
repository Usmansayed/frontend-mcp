"""EXP-027 Adoption — evidence before implementation + coordinator visibility."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E27 = ROOT / "evals/decision_lab/experiments/EXP-027-adoption-evidence-before-impl/scenarios"


@pytest.mark.unit
def test_exp027_greenfield_evidence_before_impl() -> None:
    r = run_scenario(E27 / "greenfield_evidence_before_impl.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp027_in_baseline_pack() -> None:
    pack = run_pack()
    ids = {r.id for r in pack.results}
    assert "exp027_greenfield_evidence_before_impl" in ids
    hit = next(r for r in pack.results if r.id == "exp027_greenfield_evidence_before_impl")
    assert hit.passed, hit.failures
