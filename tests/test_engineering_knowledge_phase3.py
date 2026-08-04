"""Phase 3 tests — adapters, SpecDiff-in-review path, A/B harness."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.engineering_knowledge import (
    compile_figma_seed_spec,
    compile_inspiration_seed_spec,
    compile_live_spec,
    diff_specs,
)


@pytest.mark.unit
def test_inspiration_seed_spec_soft_priors_not_geometry() -> None:
    spec = compile_inspiration_seed_spec(
        query="saas dashboard admin",
        profiles=[{"page_type": "dashboard", "style": "product", "components": ["sidebar", "table"]}],
    )
    assert spec.source_kind == "inspiration_seed"
    arch = spec.decision("layout.archetype")
    assert arch is not None
    assert arch.status == "partial"
    assert arch.value == "left_sidebar_dashboard"
    assert arch.confidence < 0.5
    # Geometry must stay unresolved until Snapshot
    assert spec.decision("layout.sidebar_width_px").status == "unresolved"
    blob = spec.to_dict()
    assert "modern" not in str(blob).lower()


@pytest.mark.unit
def test_figma_seed_spec_accent_from_tokens() -> None:
    spec = compile_figma_seed_spec(
        {
            "tokens": {"Primary/Default": "#112233", "primary": "#112233"},
            "fonts": ["Geist", "Inter"],
            "frames": [{"size": {"width": 1280, "height": 800}}],
        }
    )
    assert spec.decision("color.accent").status == "partial"
    assert spec.decision("type.font_families").status == "partial"
    assert spec.decision("layout.content_max_width_px").status == "partial"


@pytest.mark.unit
def test_ab_harness_saas_dashboard_passes() -> None:
    from evals.engineering_spec_ab.run import run_scenario

    result = run_scenario(
        {
            "id": "saas_dashboard",
            "task": "Build a SaaS dashboard",
            "fixture": "dashboard",
            "min_influence_gain": 0.35,
        }
    )
    assert result.score_with > result.score_without
    assert result.influence_gain >= 0.35
    assert result.passed


@pytest.mark.unit
def test_ab_harness_drift_produces_specdiff() -> None:
    from evals.engineering_spec_ab.run import run_scenario

    result = run_scenario(
        {
            "id": "dashboard_drift",
            "task": "Review dashboard vs reference",
            "fixture": "dashboard",
            "mutate_sidebar": 200,
            "min_influence_gain": 0.35,
        }
    )
    assert result.engineering_delta is not None
    assert result.engineering_delta["summary"]["delta_count"] >= 1
    ids = {i["decision_id"] for i in result.engineering_delta["items"]}
    assert "layout.sidebar_width_px" in ids


@pytest.mark.unit
def test_reference_vs_live_specdiff_on_fixture() -> None:
    fixture = {
        "url": "http://localhost:5173/",
        "viewport": {"width": 1280, "height": 720},
        "document": {"scrollWidth": 1280, "scrollHeight": 800},
        "css_variables": {"--primary": "#0000ff"},
        "elements": [
            {
                "tag": "nav",
                "selector": "nav",
                "text": "Nav",
                "classes": [],
                "rect": {"width": 260, "height": 720},
                "style": {
                    "fontSize": "14px",
                    "fontFamily": "Inter",
                    "color": "#111",
                    "backgroundColor": "#fafafa",
                    "padding": "8px",
                },
            },
            {
                "tag": "main",
                "selector": "main",
                "text": "",
                "classes": [],
                "rect": {"width": 1000, "height": 720},
                "style": {
                    "fontSize": "16px",
                    "fontFamily": "Inter",
                    "color": "#333",
                    "backgroundColor": "#fff",
                    "padding": "16px",
                },
            },
            {
                "tag": "h1",
                "selector": "h1",
                "text": "Title",
                "classes": [],
                "style": {
                    "fontSize": "24px",
                    "fontFamily": "Inter",
                    "color": "#111",
                    "backgroundColor": "transparent",
                },
            },
        ],
    }
    snap = DesignSnapshotEngine().capture_from_fixture(fixture)
    snap.layout.regions = [
        {"role": "nav", "rect": {"width": 260, "height": 720}},
        {"role": "main", "rect": {"width": 1000, "height": 720}},
    ]
    ref = compile_live_spec(snap)
    cur = compile_live_spec(snap)
    cur.decisions["layout.sidebar_width_px"].value = 200
    delta = diff_specs(ref, cur)
    assert any(i.decision_id == "layout.sidebar_width_px" for i in delta.items)
