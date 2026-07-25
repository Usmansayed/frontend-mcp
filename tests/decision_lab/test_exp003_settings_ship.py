"""EXP-003 settings surface ship via lab episode."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.lab import DecisionLayerLab
from navigation.coordination_intelligence.planning.ship_council import build_ship_council
from navigation.design_snapshot_engine.models import DesignSnapshot

SETTINGS_SNAP = {
    "url": "http://localhost:5173/settings",
    "layout": {
        "viewport": {"width": 1280, "height": 720},
        "regions": [
            {"role": "sidebar", "width_ratio": 0.18},
            {
                "role": "main",
                "label": "settings",
                "width_ratio": 0.95,
                "rect": {"x": 220, "y": 0, "w": 1060, "h": 720},
            },
        ],
        "interactive_boxes": [
            {"x": 400, "y": 680, "w": 80, "h": 32},
            {"x": 500, "y": 680, "w": 80, "h": 32},
        ],
    },
    "hierarchy": {
        "prominence_scores": [
            {"score": 0.5, "label": "a"},
            {"score": 0.5, "label": "b"},
            {"score": 0.5, "label": "c"},
        ],
    },
    "colors": {"token_backed_ratio": 0.8},
}


@pytest.mark.unit
def test_exp003_settings_ship_signals_from_episode() -> None:
    lab = DecisionLayerLab()
    lab.start("redesign workspace settings preferences")
    assert lab.snapshot()["surface_type"] == "settings_form"
    psm = lab.service.runtime.require(lab.episode_id)
    strategy = lab.snapshot()["strategy"]
    ship = build_ship_council(
        psm=psm,
        strategy=strategy,
        snapshot=DesignSnapshot.from_dict(SETTINGS_SNAP),
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    signals = {c["signal"] for c in ship["challenges"]}
    assert "settings_form_measure" in signals
    assert "equal_weight_kpi_cluster" not in signals
    assert ship["ship_gate"].get("surface_type") == "settings_form"
