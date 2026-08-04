"""End-to-end validation: live-shaped extractors → Ship Council → coordination hints."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel, _utc_now
from navigation.coordination_intelligence.planning.engineering_strategy import compile_engineering_strategy
from navigation.coordination_intelligence.planning.ship_council import (
    assess_snapshot_coverage,
    build_ship_council,
    ship_council_hint,
)
from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.design_snapshot_engine.raw_context import RawBrowserContext
from navigation.mcp.design_intelligence_handlers import handle_design_review
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


DASHBOARD_RAW = {
    "url": "http://localhost:5173/dashboard",
    "viewport": {"width": 1280, "height": 720},
    "document": {"scrollWidth": 1280, "scrollHeight": 1400},
    "css_variables": {},
    "elements": [
        {
            "tag": "nav",
            "classes": ["sidebar"],
            "text": "Dashboard Analytics Settings",
            "rect": {"x": 0, "y": 0, "w": 220, "h": 1400},
            "style": {"position": "static", "display": "block", "fontSize": "14px"},
        },
        {
            "tag": "main",
            "classes": [],
            "text": "Overview",
            "rect": {"x": 320, "y": 40, "w": 640, "h": 900},
            "style": {"position": "static", "display": "block", "fontSize": "16px"},
        },
        {"tag": "h2", "text": "Revenue", "style": {"fontSize": "24px"}, "rect": {"x": 340, "y": 90, "w": 200, "h": 40}},
        {"tag": "h2", "text": "Users", "style": {"fontSize": "24px"}, "rect": {"x": 560, "y": 90, "w": 200, "h": 40}},
        {"tag": "h2", "text": "Churn", "style": {"fontSize": "23px"}, "rect": {"x": 780, "y": 90, "w": 200, "h": 40}},
        {"tag": "section", "text": "KPI", "rect": {"x": 220, "y": 80, "w": 1000, "h": 140}, "style": {"display": "block"}},
        {"tag": "section", "text": "Chart", "rect": {"x": 220, "y": 240, "w": 1000, "h": 300}, "style": {"display": "block"}},
        {"tag": "section", "text": "Table", "rect": {"x": 220, "y": 560, "w": 1000, "h": 400}, "style": {"display": "block"}},
        {"tag": "header", "text": "App", "rect": {"x": 220, "y": 0, "w": 1060, "h": 56}, "style": {"display": "block"}},
        {"tag": "footer", "text": "Footer", "rect": {"x": 220, "y": 1300, "w": 1060, "h": 40}, "style": {"display": "block"}},
        {
            "tag": "button",
            "text": "Export",
            "classes": ["primary"],
            "rect": {"x": 900, "y": 12, "w": 100, "h": 32},
            "style": {"color": "#111", "backgroundColor": "#22c55e", "fontSize": "13px", "padding": "8px"},
        },
    ],
    "visual_insights": {
        "issues": [],
        "blocking": [],
        "element_boxes": [
            {"x": 240, "y": 90, "w": 220, "h": 100},
            {"x": 480, "y": 90, "w": 220, "h": 100},
            {"x": 720, "y": 90, "w": 220, "h": 100},
            {"x": 960, "y": 90, "w": 220, "h": 100},
        ],
    },
}


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> int:
    engine = DesignSnapshotEngine()
    snapshot = engine.capture_from_fixture(DASHBOARD_RAW)
    layout = snapshot.layout
    assert layout.regions, "regions missing"
    nav = next((r for r in layout.regions if r.get("role") in ("nav", "aside")), None)
    assert nav and "position" in nav and "width_ratio" in nav, f"nav not enriched: {nav}"
    main_r = next((r for r in layout.regions if r.get("role") == "main"), None)
    assert main_r and main_r.get("centered") is True, f"main not centered: {main_r}"
    assert snapshot.hierarchy.prominence_scores
    assert all("normalized" in p for p in snapshot.hierarchy.prominence_scores)
    _ok("extractor enrichment (position/width/centered/normalized)")

    coverage = assess_snapshot_coverage(snapshot)
    assert coverage["coverage"] in ("full", "partial"), coverage
    _ok(f"coverage={coverage['coverage']} score={coverage['score']}")

    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_validate"
    psm.episode.verification_status = "passed"
    psm.episode.intent_stack = [
        IntentFrame(intent="build a new SaaS analytics dashboard", pushed_at=_utc_now()),
    ]
    bundle = load_runtime_artifacts()
    strategy = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
    hint = ship_council_hint(strategy, psm)
    assert hint and hint.get("mode") == "ship", hint
    _ok(f"ship_council_hint -> {hint.get('resource')}")

    ship = build_ship_council(
        psm=psm,
        strategy={**strategy, "influence_level": "structural", "task_scope": "design_driven"},
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    signals = {c["signal"] for c in ship["challenges"]}
    needed = {"nav_not_sticky", "narrow_centered_main"}
    if not needed.issubset(signals):
        _fail(f"expected {needed}, got {signals}")
    if ship["ship_gate"]["council_clear"]:
        _fail("council should not clear with open layout challenges")
    _ok(f"challenges={sorted(signals)} gate={ship['ship_gate']['state']}")

    # Handler path with explicit ship mode
    snaps = SnapshotRegistry()
    rec = snaps.register(snapshot=snapshot.to_dict(), url=snapshot.url)
    result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snaps,
            {
                "snapshot_id": rec.snapshot_id,
                "user_task": "build a new SaaS analytics dashboard",
                "mode": "ship",
            },
        )
    )
    data = result["data"]
    if not result.get("ok") or data.get("mode") != "ship":
        _fail(f"handler failed: {result}")
    h_signals = {c["signal"] for c in data.get("challenges") or []}
    if "nav_not_sticky" not in h_signals:
        _fail(f"handler missing nav_not_sticky: {h_signals}")
    if data["ship_gate"].get("council_clear") is not False:
        _fail(f"handler cleared incorrectly: {data['ship_gate']}")
    coverage_hint = (data.get("agent_summary") or {}).get("ship_council_hint") or {}
    if "coverage" not in coverage_hint:
        _fail(f"missing coverage in hint: {coverage_hint}")
    _ok(f"handler challenges={sorted(h_signals)} coverage={data['ship_gate'].get('coverage')}")

    # Sparse login should clear with low confidence
    sparse_ctx = RawBrowserContext(
        url="http://localhost:5173/login",
        viewport={"width": 1280, "height": 720},
        document={"scrollWidth": 1280, "scrollHeight": 720},
        elements=[
            {
                "tag": "main",
                "rect": {"x": 0, "y": 0, "w": 1280, "h": 720},
                "style": {"position": "static", "display": "block"},
                "text": "",
            },
            {
                "tag": "form",
                "rect": {"x": 440, "y": 200, "w": 400, "h": 300},
                "style": {"position": "static", "display": "block"},
                "text": "Login",
            },
            {"tag": "h1", "text": "Sign in", "style": {"fontSize": "28px"}},
        ],
        css_variables={"--primary": "#2563eb"},
        visual_insights={"issues": [], "blocking": [], "element_boxes": []},
    )
    from navigation.design_snapshot_engine.extractors.layout import LayoutExtractor
    from navigation.design_snapshot_engine.extractors.hierarchy import HierarchyExtractor
    from navigation.design_snapshot_engine.models import DesignSnapshot

    layout_out = LayoutExtractor().extract(sparse_ctx)["layout"]
    hier_out = HierarchyExtractor().extract(sparse_ctx)["hierarchy"]
    color_out = {"token_backed_ratio": 0.82, "raw_color_count": 3}
    sparse_snap = DesignSnapshot.from_dict({
        "url": sparse_ctx.url,
        "layout": layout_out,
        "hierarchy": hier_out,
        "colors": color_out,
        "design_tokens": {},
    })
    sparse_ship = build_ship_council(
        psm=ProjectSituationModel(),
        strategy={"influence_level": "structural", "task_scope": "design_driven", "unresolved_decisions": []},
        snapshot=sparse_snap,
        engineering_delta=None,
        revision_gate={},
        findings=[],
        force=True,
    )
    conf = (sparse_ship.get("ship_summary") or {}).get("ship_confidence", 1.0)
    if sparse_ship["ship_gate"]["council_clear"] is not True:
        _fail(f"sparse should clear: {sparse_ship['ship_gate']} challenges={sparse_ship['challenges']}")
    if conf > 0.65:
        _fail(f"sparse confidence too high: {conf}")
    _ok(f"sparse clear confidence={conf} coverage={sparse_ship['ship_gate'].get('coverage')}")

    print("VALIDATE_SHIP_COUNCIL_LOOP: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
