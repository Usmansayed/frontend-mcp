"""EXP-011 / 012 / 013 session tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab.runner import (
    run_pack,
    run_scenario,
    write_scorecard,
)

E13 = ROOT / "evals/decision_lab/experiments/EXP-013-host-portfolio-hint/scenarios"


@pytest.mark.unit
def test_exp011_baseline_is_default_pack() -> None:
    pack = run_pack()  # default → baseline
    assert pack.pack_id == "baseline"
    assert pack.pass_count >= 25
    assert pack.passed, pack.scorecard()


@pytest.mark.unit
def test_exp012_scorecard_write(tmp_path: Path) -> None:
    pack = run_pack(pack="smoke")
    out = write_scorecard(pack, tmp_path / "scorecard.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["pack_id"] == "smoke"
    assert data["passed"] is True
    assert data["total"] == 6


@pytest.mark.unit
def test_exp013_host_lists_unpaid_portfolio() -> None:
    r = run_scenario(E13 / "host_lists_unpaid.yaml")
    assert r.passed, r.failures
    host = r.final_snapshot.get("host_action") or ""
    assert "Portfolio unpaid:" in host
    assert "do not tunnel" in host
