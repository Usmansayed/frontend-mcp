"""EXP-004 snapshot supersedes design_reference."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

EXP = ROOT / "evals/decision_lab/experiments/EXP-004-snapshot-supersede/scenarios"


@pytest.mark.unit
def test_exp004_snapshot_clears_design_reference_from_backlog_top() -> None:
    result = run_scenario(EXP / "snapshot_clears_reference.yaml")
    assert result.passed, result.failures
