"""Tests for FrontendEngineeringSpec V1 — catalog, Knowledge Compiler, SpecDiff."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.engineering_knowledge import (
    EngineeringKnowledgeCompiler,
    catalog_ids,
    diff_specs,
)
from navigation.engineering_knowledge.catalog import V1_DECISION_DEFS
from navigation.engineering_knowledge.models import V1_GROUPS as MODEL_GROUPS


@pytest.fixture
def dashboard_fixture() -> dict:
    return {
        "url": "http://localhost:5173/dashboard",
        "viewport": {"width": 1440, "height": 900},
        "document": {"scrollWidth": 1440, "scrollHeight": 1200},
        "css_variables": {
            "--primary": "#4f46e5",
            "--spacing-2": "8px",
            "--spacing-4": "16px",
            "--spacing-8": "32px",
        },
        "elements": [
            {
                "tag": "nav",
                "selector": "nav.sidebar",
                "text": "Dashboard",
                "classes": ["sidebar"],
                "rect": {"x": 0, "y": 0, "width": 280, "height": 900},
                "style": {
                    "fontSize": "14px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(17, 24, 39)",
                    "backgroundColor": "rgb(249, 250, 251)",
                    "padding": "16px",
                    "margin": "0px",
                },
            },
            {
                "tag": "header",
                "selector": "header",
                "text": "Overview",
                "classes": [],
                "rect": {"x": 280, "y": 0, "width": 1160, "height": 72},
                "style": {
                    "fontSize": "18px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(17, 24, 39)",
                    "backgroundColor": "rgb(255, 255, 255)",
                    "padding": "16px",
                    "margin": "0px",
                },
            },
            {
                "tag": "main",
                "selector": "main",
                "text": "",
                "classes": [],
                "rect": {"x": 280, "y": 72, "width": 1160, "height": 828},
                "style": {
                    "fontSize": "16px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(55, 65, 81)",
                    "backgroundColor": "rgb(255, 255, 255)",
                    "padding": "24px",
                    "margin": "0px",
                    "gap": "24px",
                },
            },
            {
                "tag": "h1",
                "selector": "h1",
                "text": "Revenue overview",
                "classes": [],
                "rect": {"x": 304, "y": 96, "width": 400, "height": 40},
                "style": {
                    "fontSize": "28px",
                    "fontFamily": "Inter, sans-serif",
                    "lineHeight": "36px",
                    "color": "rgb(17, 24, 39)",
                    "backgroundColor": "rgba(0, 0, 0, 0)",
                    "padding": "0px",
                    "margin": "0px 0px 16px",
                },
            },
            {
                "tag": "h2",
                "selector": "h2",
                "text": "This week",
                "classes": [],
                "rect": {"x": 304, "y": 160, "width": 200, "height": 28},
                "style": {
                    "fontSize": "20px",
                    "fontFamily": "Inter, sans-serif",
                    "lineHeight": "28px",
                    "color": "rgb(17, 24, 39)",
                    "backgroundColor": "rgba(0, 0, 0, 0)",
                    "padding": "0px",
                    "margin": "0px 0px 12px",
                },
            },
            {
                "tag": "p",
                "selector": "p",
                "text": "Body copy for metrics.",
                "classes": [],
                "rect": {"x": 304, "y": 200, "width": 480, "height": 24},
                "style": {
                    "fontSize": "16px",
                    "fontFamily": "Inter, sans-serif",
                    "lineHeight": "24px",
                    "color": "rgb(55, 65, 81)",
                    "backgroundColor": "rgb(255, 255, 255)",
                    "padding": "0px",
                    "margin": "0px 0px 24px",
                },
            },
            {
                "tag": "button",
                "selector": "button.primary",
                "text": "Export",
                "classes": ["primary"],
                "rect": {"x": 1200, "y": 20, "width": 96, "height": 36},
                "style": {
                    "fontSize": "14px",
                    "color": "#ffffff",
                    "backgroundColor": "#4f46e5",
                    "padding": "8px 16px",
                    "borderRadius": "8px",
                },
            },
        ],
    }


@pytest.mark.unit
def test_v1_catalog_is_pareto_sized() -> None:
    assert MODEL_GROUPS == (
        "layout",
        "information_hierarchy",
        "navigation_model",
        "spacing_system",
        "typography",
        "color_system",
        "component_foundation",
        "visual_density",
    )
    ids = catalog_ids()
    assert 20 <= len(ids) <= 40
    assert len(ids) == len(set(ids))
    groups = {d.group for d in V1_DECISION_DEFS}
    assert groups <= set(MODEL_GROUPS)


@pytest.mark.unit
def test_empty_spec_all_unresolved() -> None:
    spec = EngineeringKnowledgeCompiler().empty_spec(source_kind="test")
    assert len(spec.decisions) == len(V1_DECISION_DEFS)
    assert all(d.status == "unresolved" for d in spec.decisions.values())
    blob = spec.to_dict()
    assert blob["coverage"]["resolved"] == 0
    assert blob["unresolved_by_impact"][0]["impact_weight"] >= blob["unresolved_by_impact"][-1][
        "impact_weight"
    ]


@pytest.mark.unit
def test_compiler_resolves_dashboard_layout(dashboard_fixture: dict) -> None:
    snapshot = DesignSnapshotEngine().capture_from_fixture(dashboard_fixture)
    # Ensure regions carry geometry for compiler (fixture path)
    if not any(r.get("role") == "nav" for r in snapshot.layout.regions):
        snapshot.layout.regions = [
            {"role": "nav", "rect": {"width": 280, "height": 900}},
            {"role": "header", "rect": {"width": 1160, "height": 72}},
            {"role": "main", "rect": {"width": 1160, "height": 828}},
        ]
    else:
        for r in snapshot.layout.regions:
            if r.get("role") == "nav" and not r.get("rect"):
                r["rect"] = {"width": 280, "height": 900}
            if r.get("role") == "header" and not r.get("rect"):
                r["rect"] = {"width": 1160, "height": 72}
            if r.get("role") == "main" and not r.get("rect"):
                r["rect"] = {"width": 1160, "height": 828}

    spec = EngineeringKnowledgeCompiler().compile_from_snapshot(
        snapshot, source_kind="live_dom"
    )
    assert spec.decision("layout.archetype").status in ("resolved", "partial")
    assert spec.decision("layout.sidebar_width_px").status == "resolved"
    assert int(spec.decision("layout.sidebar_width_px").value) == 280
    assert spec.decision("nav.pattern").value == "left_sidebar"
    assert spec.decision("layout.sidebar_width_px").impact_weight >= 0.9
    # Decisions not adjectives
    assert "modern" not in str(spec.to_dict()).lower()
    assert "clean" not in str(spec.to_dict()).lower()


@pytest.mark.unit
def test_spec_diff_flags_sidebar_drift(dashboard_fixture: dict) -> None:
    snapshot = DesignSnapshotEngine().capture_from_fixture(dashboard_fixture)
    snapshot.layout.regions = [
        {"role": "nav", "rect": {"width": 280, "height": 900}},
        {"role": "header", "rect": {"width": 1160, "height": 72}},
        {"role": "main", "rect": {"width": 1160, "height": 828}},
    ]
    ref = EngineeringKnowledgeCompiler().compile_from_snapshot(snapshot, source_kind="reference")
    current = EngineeringKnowledgeCompiler().compile_from_snapshot(snapshot, source_kind="live_dom")
    current.decisions["layout.sidebar_width_px"].value = 200
    delta = diff_specs(ref, current)
    assert delta.summary["delta_count"] >= 1
    ids = {i.decision_id for i in delta.items}
    assert "layout.sidebar_width_px" in ids
    sidebar = next(i for i in delta.items if i.decision_id == "layout.sidebar_width_px")
    assert sidebar.kind in ("value_drift", "enum_mismatch")
    assert sidebar.impact_weight >= 0.9
