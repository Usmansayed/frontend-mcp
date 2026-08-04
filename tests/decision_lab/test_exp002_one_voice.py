"""EXP-002 one-voice tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

EXP = ROOT / "evals/decision_lab/experiments/EXP-002-one-voice/scenarios"


@pytest.mark.unit
def test_exp002_suggested_matches_gate_next() -> None:
    result = run_scenario(EXP / "one_voice_after_observe.yaml")
    assert result.passed, result.failures
