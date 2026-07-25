"""EXP-023 Perfect Layer Phase B episode_card."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import run_pack, run_scenario

E23 = ROOT / "evals/decision_lab/experiments/EXP-023-episode-card/scenarios"


@pytest.mark.unit
def test_exp023_episode_card_readout() -> None:
    r = run_scenario(E23 / "episode_card_readout.yaml")
    assert r.passed, r.failures
    card = (r.final_snapshot or {}).get("episode_card") or {}
    assert card.get("schema") == "episode_card.v1"
    assert card.get("what_matters")


@pytest.mark.unit
def test_exp023_baseline_includes_episode_card() -> None:
    pack = run_pack()
    assert pack.pack_id == "baseline"
    assert len(pack.results) >= 25
    assert pack.passed, pack.scorecard()
    assert "exp023_episode_card_readout" in {r.id for r in pack.results}
