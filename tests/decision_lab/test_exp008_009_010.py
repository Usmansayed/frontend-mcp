"""EXP-008 / 009 / 010 session tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

E8 = ROOT / "evals/decision_lab/experiments/EXP-008-ship-residue-claim/scenarios"
E9 = ROOT / "evals/decision_lab/experiments/EXP-009-codebase-claim/scenarios"
E10 = ROOT / "evals/decision_lab/experiments/EXP-010-evidence-status-alias/scenarios"


@pytest.mark.unit
def test_exp008_ship_residue_claim() -> None:
    r = run_scenario(E8 / "ship_residue_claim.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp009_codebase_does_not_block_claim() -> None:
    r = run_scenario(E9 / "codebase_does_not_block_claim.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp010_component_status_alias() -> None:
    r = run_scenario(E10 / "component_status_alias.yaml")
    assert r.passed, r.failures
