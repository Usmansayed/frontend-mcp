"""EXP-001 characterizing + regression tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

EXP = (
    ROOT
    / "evals"
    / "decision_lab"
    / "experiments"
    / "EXP-001-family-visibility"
    / "scenarios"
)


@pytest.mark.unit
def test_exp001_ship_host_aligns_after_verify() -> None:
    result = run_scenario(EXP / "ship_host_aligns.yaml")
    assert result.passed, result.failures
