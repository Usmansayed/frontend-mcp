"""EXP-014 / 015 synthesis session tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E15 = ROOT / "evals/decision_lab/experiments/EXP-015-settings-ship-baseline/scenarios"
SYNTHESIS = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-18-final-coordination-layer-synthesis.md"
)


@pytest.mark.unit
def test_exp014_synthesis_doc_exists() -> None:
    text = SYNTHESIS.read_text(encoding="utf-8")
    assert "Final Coordination Layer" in text
    assert "pause Coordination Intelligence feature growth" in text
    assert "episode_portfolio" in text
    assert "packs/baseline.yaml" in text


@pytest.mark.unit
def test_exp015_settings_ship_baseline_scenario() -> None:
    r = run_scenario(E15 / "settings_ship_baseline.yaml")
    assert r.passed, r.failures
    signals = set((r.final_snapshot.get("last_ship") or {}).get("signals") or [])
    assert "settings_form_measure" in signals
    assert "equal_weight_kpi_cluster" not in signals


@pytest.mark.unit
def test_exp015_baseline_includes_settings_ship() -> None:
    pack = run_pack(pack="baseline")
    ids = {r.id for r in pack.results}
    assert "exp015_settings_ship_baseline" in ids
    assert pack.passed, pack.scorecard()
