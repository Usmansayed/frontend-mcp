"""Phase C route-aware Meridian surfaces."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.route_surfaces import (
    active_route_surface,
    derive_route_surface,
    normalize_route_path,
    promote_mixed_from_routes,
    upsert_route_surface,
)
from navigation.coordination_intelligence.planning.ship_council import build_ship_council
from navigation.design_snapshot_engine.models import DesignSnapshot


@pytest.mark.unit
def test_normalize_route_path() -> None:
    assert normalize_route_path("http://localhost:5173/settings?x=1") == "/settings"
    assert normalize_route_path("/dashboard/") == "/dashboard"


@pytest.mark.unit
def test_derive_route_surface_from_path() -> None:
    assert derive_route_surface("/settings") == "settings_form"
    assert derive_route_surface("/dashboard") == "dashboard"
    assert derive_route_surface("/about") == "marketing"
    assert derive_route_surface("/portfolio") == "marketing"


@pytest.mark.unit
def test_upsert_promotes_mixed_and_sets_active() -> None:
    psm = ProjectSituationModel()
    upsert_route_surface(psm, "http://localhost:5173/dashboard", family="observe")
    upsert_route_surface(psm, "http://localhost:5173/settings", family="observe")
    assert psm.episode.surface_type == "mixed"
    assert psm.episode.active_route_path == "/settings"
    assert active_route_surface(psm) == "settings_form"
    assert promote_mixed_from_routes(psm) == "mixed"


@pytest.mark.unit
def test_ship_uses_active_route_surface_on_mixed() -> None:
    psm = ProjectSituationModel()
    psm.episode.surface_type = "mixed"
    psm.episode.verification_status = "passed"
    upsert_route_surface(psm, "http://localhost:5173/dashboard", family="snapshot")
    upsert_route_surface(psm, "http://localhost:5173/settings", family="snapshot")
    snap = DesignSnapshot.from_dict({
        "url": "http://localhost:5173/settings",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "regions": [
                {"role": "sidebar"},
                {"role": "main", "label": "settings", "rect": {"x": 220, "y": 0, "w": 1060, "h": 720}},
                {"role": "form"},
            ],
            "interactive_boxes": [{"x": i, "y": 0, "w": 10, "h": 10} for i in range(20)],
        },
        "hierarchy": {"prominence_scores": [0.5, 0.5, 0.5, 0.5]},
    })
    ship = build_ship_council(
        psm=psm,
        strategy={"influence_level": "structural", "task_scope": "redesign", "surface_type": "mixed"},
        snapshot=snap,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    gate = ship.get("ship_gate") or {}
    assert gate.get("surface_type") == "settings_form"
    assert gate.get("active_route") == "/settings"
    signals = {c.get("signal") for c in ship.get("challenges") or []}
    assert "equal_weight_kpi_cluster" not in signals


@pytest.mark.unit
def test_ship_does_not_clobber_active_route_with_stale_snapshot_url() -> None:
    """Historical dashboard snapshot must not override live /settings active route."""
    psm = ProjectSituationModel()
    psm.episode.surface_type = "mixed"
    psm.episode.verification_status = "passed"
    upsert_route_surface(psm, "http://localhost:5173/dashboard", family="snapshot")
    upsert_route_surface(psm, "http://localhost:5173/settings/profile", family="observe")
    assert psm.episode.active_route_path == "/settings/profile"

    stale_dash_snap = DesignSnapshot.from_dict({
        "url": "http://localhost:5173/dashboard",
        "snapshot_id": "snap_stale_dash",
        "layout": {
            "viewport": {"width": 1280, "height": 720},
            "regions": [
                {"role": "sidebar"},
                {"role": "main", "label": "dashboard"},
            ],
            "interactive_boxes": [{"x": i * 100, "y": 40, "w": 90, "h": 80} for i in range(4)],
        },
        "hierarchy": {"prominence_scores": [0.5, 0.5, 0.5, 0.5]},
    })
    ship = build_ship_council(
        psm=psm,
        strategy={"influence_level": "structural", "task_scope": "redesign", "surface_type": "mixed"},
        snapshot=stale_dash_snap,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    gate = ship.get("ship_gate") or {}
    assert psm.episode.active_route_path == "/settings/profile"
    assert gate.get("active_route") == "/settings/profile"
    assert gate.get("surface_type") == "settings_form"
    signals = {c.get("signal") for c in ship.get("challenges") or []}
    assert "equal_weight_kpi_cluster" not in signals


@pytest.mark.unit
def test_upsert_set_active_false_preserves_active_route() -> None:
    psm = ProjectSituationModel()
    upsert_route_surface(psm, "/settings", family="observe")
    upsert_route_surface(psm, "/dashboard", family="snapshot", set_active=False)
    assert psm.episode.active_route_path == "/settings"
    assert "/dashboard" in (psm.episode.route_surfaces or {})


@pytest.mark.unit
def test_apply_envelope_execute_actions_upserts_route() -> None:
    from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
    from navigation.coordination_intelligence.psm.normalize import apply_envelope

    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    apply_envelope(
        psm,
        {
            "tool": "perception_execute_actions",
            "ok": True,
            "url": "http://localhost:5173/settings/profile",
            "scan_id": "scan_actions_1",
            "data": {"actions_ok": True},
        },
        bundle,
    )
    assert psm.episode.active_route_path == "/settings/profile"
    assert active_route_surface(psm) == "settings_form"


@pytest.mark.unit
def test_apply_envelope_bare_navigate_updates_active_route() -> None:
    """Run 6b bug H: perception_navigate must move active_route even without observe."""
    from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
    from navigation.coordination_intelligence.psm.normalize import apply_envelope

    psm = ProjectSituationModel()
    bundle = load_runtime_artifacts()
    upsert_route_surface(psm, "http://127.0.0.1:3001/about/", family="observe")
    assert psm.episode.active_route_path == "/about"
    apply_envelope(
        psm,
        {
            "tool": "perception_navigate",
            "ok": True,
            "url": "http://127.0.0.1:3001/work/",
            "data": {"preflight": {"ok": True}},
        },
        bundle,
    )
    assert psm.episode.active_route_path == "/work"
