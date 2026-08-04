"""Decision Layer Lab — core + pack tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab import DecisionLayerLab, run_pack, run_scenario
from navigation.coordination_intelligence.lab.expect import ExpectationError
from navigation.coordination_intelligence.lab.runner import (
    default_scenarios_dir,
    resolve_pack_scenario_paths,
)


@pytest.mark.unit
def test_lab_start_and_snapshot() -> None:
    lab = DecisionLayerLab()
    eid = lab.start("build a new SaaS analytics dashboard")
    assert eid
    snap = lab.snapshot()
    assert snap["surface_type"] == "dashboard"
    assert snap["gate"]["state"] == "blocked"
    lab.expect(gate_state="blocked", surface_type="dashboard")


@pytest.mark.unit
def test_lab_expect_fails() -> None:
    lab = DecisionLayerLab()
    lab.start("build a new SaaS analytics dashboard")
    with pytest.raises(ExpectationError):
        lab.expect(gate_state="ready")


@pytest.mark.unit
def test_lab_inspiration_fail_fallback() -> None:
    lab = DecisionLayerLab()
    lab.start("build a new SaaS analytics dashboard")
    lab.feed("perception_inspiration_collect", ok=False, error="blobs failed")
    lab.expect(next_capability="browser_observe")


@pytest.mark.unit
def test_run_single_scenario_file() -> None:
    path = default_scenarios_dir() / "03_hotfix_surgical.yaml"
    result = run_scenario(path)
    assert result.passed, result.failures


@pytest.mark.unit
def test_smoke_pack() -> None:
    pack = run_pack(pack="smoke")
    assert pack.pack_id == "smoke"
    assert pack.pass_count == 6
    assert pack.passed, pack.scorecard()


@pytest.mark.unit
def test_baseline_pack() -> None:
    pack_id, paths = resolve_pack_scenario_paths("baseline")
    assert pack_id == "baseline"
    assert len(paths) >= 15
    pack = run_pack(pack="baseline")
    assert pack.pack_id == "baseline"
    assert pack.passed, pack.scorecard()


@pytest.mark.unit
def test_full_decision_lab_pack_directory_legacy() -> None:
    pack = run_pack(directory=default_scenarios_dir())
    assert pack.results, "no scenarios found"
    assert pack.passed, pack.scorecard()
