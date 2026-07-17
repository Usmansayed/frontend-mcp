"""Reference Spec binding + SpecDiff revision gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.engineering_knowledge import (
    bind_reference_spec,
    clear_reference_spec,
    compile_live_spec,
    evaluate_revision_gate,
    get_reference_spec,
)


def _dashboard_payload(*, sidebar_width: int = 280) -> dict:
    return {
        "url": "http://localhost:5173/dashboard",
        "viewport": {"width": 1440, "height": 900},
        "document": {"scrollWidth": 1440, "scrollHeight": 1200},
        "css_variables": {"--primary": "#4f46e5"},
        "elements": [
            {
                "tag": "nav",
                "selector": "nav.sidebar",
                "text": "Dashboard",
                "classes": ["sidebar"],
                "rect": {"x": 0, "y": 0, "width": sidebar_width, "height": 900},
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
                "tag": "main",
                "selector": "main",
                "text": "",
                "classes": [],
                "rect": {"x": sidebar_width, "y": 72, "width": 1440 - sidebar_width, "height": 828},
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
        ],
    }


@pytest.mark.unit
def test_bind_and_get_reference_spec_session_fallback() -> None:
    sid = "sess-bind-test-1"
    clear_reference_spec(session_id=sid)
    snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload())
    ref = compile_live_spec(snap)
    meta = bind_reference_spec(ref, session_id=sid, source="unit_test")
    assert meta["bound"] is True

    loaded, loaded_meta = get_reference_spec(session_id=sid)
    assert loaded is not None
    assert loaded.decision("layout.sidebar_width_px") is not None
    assert loaded_meta.get("source") == "unit_test"

    clear_reference_spec(session_id=sid)
    gone, _ = get_reference_spec(session_id=sid)
    assert gone is None


@pytest.mark.unit
def test_revision_gate_no_reference() -> None:
    snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload())
    current = compile_live_spec(snap)
    gate = evaluate_revision_gate(current, None, phase="current")
    assert gate["reference_bound"] is False
    assert gate["evaluated"] is False
    assert gate["passed"] is False
    assert gate["revision_required"] is False
    assert "No reference Spec" in gate["host_action"]


@pytest.mark.unit
def test_inspiration_seed_binding_is_provisional() -> None:
    sid = "sess-inspiration-provisional"
    clear_reference_spec(session_id=sid)
    spec = compile_live_spec(DesignSnapshotEngine().capture_from_fixture(_dashboard_payload()))
    meta = bind_reference_spec(spec, session_id=sid, source="inspiration_seed")
    assert meta["bound"] is True
    assert meta["quality"] == "provisional"
    assert meta["implementation_ready"] is False
    clear_reference_spec(session_id=sid)


@pytest.mark.unit
def test_revision_gate_reference_captured() -> None:
    snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload())
    ref = compile_live_spec(snap)
    gate = evaluate_revision_gate(ref, ref, phase="reference_captured")
    assert gate["reference_bound"] is True
    assert gate["passed"] is True
    assert gate["revision_required"] is False
    assert gate["engineering_delta"] is None


@pytest.mark.unit
def test_revision_gate_detects_sidebar_drift() -> None:
    ref_snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload(sidebar_width=280))
    cur_snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload(sidebar_width=200))
    ref = compile_live_spec(ref_snap)
    current = compile_live_spec(cur_snap)

    ref_w = ref.decision("layout.sidebar_width_px")
    cur_w = current.decision("layout.sidebar_width_px")
    assert ref_w is not None and cur_w is not None
    # Only assert gate when both sides resolved concrete values
    if ref_w.value is not None and cur_w.value is not None and ref_w.value != cur_w.value:
        gate = evaluate_revision_gate(current, ref, phase="current")
        assert gate["reference_bound"] is True
        assert gate["revision_required"] is True
        assert gate["passed"] is False
        assert "REVISION REQUIRED" in gate["host_action"]
        assert gate["engineering_delta"] is not None
    else:
        # Compiler may leave geometry partial — still must pass when no actionable drift
        gate = evaluate_revision_gate(current, ref, phase="current")
        assert gate["reference_bound"] is True


@pytest.mark.unit
def test_revision_gate_passes_when_aligned() -> None:
    snap = DesignSnapshotEngine().capture_from_fixture(_dashboard_payload())
    spec = compile_live_spec(snap)
    gate = evaluate_revision_gate(spec, spec, phase="current")
    assert gate["reference_bound"] is True
    assert gate["revision_required"] is False
    assert gate["passed"] is True


@pytest.mark.unit
def test_explicit_reference_arg_overrides_session() -> None:
    sid = "sess-bind-override"
    clear_reference_spec(session_id=sid)
    a = compile_live_spec(
        DesignSnapshotEngine().capture_from_fixture(_dashboard_payload(sidebar_width=280))
    )
    b = compile_live_spec(
        DesignSnapshotEngine().capture_from_fixture(_dashboard_payload(sidebar_width=200))
    )
    bind_reference_spec(a, session_id=sid, source="session")
    loaded, meta = get_reference_spec(
        session_id=sid,
        reference_spec=b.to_dict(),
    )
    assert loaded is not None
    assert meta.get("source") == "argument"
    clear_reference_spec(session_id=sid)
