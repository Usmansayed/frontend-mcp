"""EXP-018 evidence quality host / agent_summary surfacing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_scenario

E18 = ROOT / "evals/decision_lab/experiments/EXP-018-evidence-host-hints/scenarios"


@pytest.mark.unit
def test_exp018_host_surfaces_thin_snapshot() -> None:
    r = run_scenario(E18 / "host_surfaces_thin_snapshot.yaml")
    assert r.passed, r.failures


@pytest.mark.unit
def test_exp018_host_surfaces_thin_clear_ship() -> None:
    r = run_scenario(E18 / "host_surfaces_thin_clear_ship.yaml")
    assert r.passed, r.failures
