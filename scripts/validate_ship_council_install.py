"""Validate installed frontend-mcp 1.2.0.dev6 Ship Council surfaces."""
from __future__ import annotations

import asyncio
import importlib.metadata as md
import sys


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> int:
    engine_ver = md.version("frontend-perception-engine")
    mcp_ver = md.version("frontend-mcp")
    if engine_ver != "1.2.0.dev6" or mcp_ver != "1.2.0.dev6":
        _fail(f"versions engine={engine_ver} mcp={mcp_ver}")
    _ok(f"versions {engine_ver}")

    ship_mod = __import__(
        "navigation.coordination_intelligence.planning.ship_council",
        fromlist=["build_ship_council"],
    )
    if "site-packages" not in (ship_mod.__file__ or ""):
        _fail(f"ship_council not from site-packages: {ship_mod.__file__}")
    _ok(f"ship_council from {ship_mod.__file__}")

    from navigation.mcp.methodology_resources import METHODOLOGY_RESOURCES
    from navigation.mcp.resources import list_resources, read_resource
    from navigation.mcp.tools import perception_tools

    if "perception://ship-council" not in METHODOLOGY_RESOURCES:
        _fail("methodology missing perception://ship-council")
    listed = {r["uri"] for r in list_resources()}
    if "perception://ship-council" not in listed:
        _fail("list_resources missing ship-council")
    mime, text, is_blob = read_resource("perception://ship-council")
    if is_blob or "Ship Council" not in text or 'mode="ship"' not in text:
        _fail("ship-council resource content invalid")
    _ok("perception://ship-council readable")

    class _T:
        Tool = type("Tool", (), {"__init__": lambda self, **kw: setattr(self, "__dict__", kw) or None})

    tools = {t.name: t for t in perception_tools(_T)}
    review = tools.get("perception_design_review")
    if not review:
        _fail("perception_design_review missing")
    props = (review.inputSchema or {}).get("properties") or {}
    if "mode" not in props or "dispositions" not in props:
        _fail("design_review schema missing mode/dispositions")
    if "mode=ship" not in review.description and "Ship Council" not in review.description:
        _fail("design_review description missing ship mode")
    _ok("perception_design_review schema/description include ship mode")

    from navigation.coordination_intelligence.models import ProjectSituationModel
    from navigation.coordination_intelligence.planning.decision_ledger import (
        apply_dispositions,
        validate_accept_reason,
    )
    from navigation.coordination_intelligence.planning.ship_council import (
        MAX_CHALLENGES,
        build_ship_council,
        ship_council_hint,
    )
    from navigation.design_snapshot_engine.models import DesignSnapshot

    ok, _ = validate_accept_reason("Looks fine.")
    if ok:
        _fail("hollow accept should fail")
    ok, _ = validate_accept_reason(
        "Sidebar is intentionally non-sticky because short pages avoid losing horizontal space on 13-inch laptops."
    )
    if not ok:
        _fail("valid accept rationale rejected")
    _ok("accept rationale validation")

    snapshot = DesignSnapshot.from_dict(
        {
            "url": "http://localhost:5173/dashboard",
            "layout": {
                "overflow_issues": [{"kind": "horizontal_overflow"}],
                "visual_insights": {
                    "blocking": ["horizontal_overflow"],
                    "issues": [{"kind": "horizontal_overflow"}],
                },
                "regions": [
                    {"role": "sidebar", "position": "static"},
                    {
                        "role": "main",
                        "centered": True,
                        "width_ratio": 0.6,
                        "layout_pattern": "marketing_centered",
                    },
                    {"role": "section"},
                    {"role": "section"},
                    {"role": "section"},
                    {"role": "section"},
                    {"role": "section"},
                ],
            },
            "hierarchy": {
                "prominence_scores": [
                    {"score": 0.5},
                    {"score": 0.51},
                    {"score": 0.5},
                ]
            },
            "colors": {"token_backed_ratio": 0.2},
        }
    )
    psm = ProjectSituationModel()
    psm.artifacts.snapshot_id = "snap_install"
    psm.episode.verification_status = "passed"
    strategy = {
        "influence_level": "structural",
        "task_scope": "design_driven",
        "unresolved_decisions": [],
        "implementation_gate": {"state": "ready"},
    }
    hint = ship_council_hint(strategy, psm)
    if not hint or hint.get("mode") != "ship":
        _fail(f"ship hint missing: {hint}")
    _ok("ship_council_hint after verify")

    ship = build_ship_council(
        psm=psm,
        strategy=strategy,
        snapshot=snapshot,
        engineering_delta=None,
        revision_gate={},
        findings=[],
    )
    if ship["mode"] != "ship":
        _fail("mode not ship")
    if not (1 <= len(ship["challenges"]) <= MAX_CHALLENGES):
        _fail(f"unexpected challenge count: {len(ship['challenges'])}")
    if ship["ship_gate"]["council_clear"] is not False:
        _fail("expected open ship gate")
    _ok(f"ship council emitted {len(ship['challenges'])} challenges")

    dispositions = [
        {
            "signal": c["signal"],
            "disposition": "accepted",
            "reason": "Matches explicit product requirement for equal metric emphasis across KPI cards.",
        }
        for c in ship["challenges"]
    ]
    applied, rejected = apply_dispositions(ship["decision_ledger"], dispositions)
    if rejected or len(applied) != len(dispositions):
        _fail(f"disposition apply failed applied={applied} rejected={rejected}")
    _ok("dispositions applied")

    from navigation.core.scan_registry import ScanRegistry
    from navigation.core.snapshot_registry import SnapshotRegistry
    from navigation.mcp.design_intelligence_handlers import handle_design_review
    from navigation.visual_browser_intelligence.browser.session_store import SessionStore

    snaps = SnapshotRegistry()
    rec = snaps.register(snapshot=snapshot.to_dict(), url=snapshot.url)
    result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snaps,
            {
                "snapshot_id": rec.snapshot_id,
                "mode": "ship",
                "user_task": "Ship analytics dashboard",
            },
        )
    )
    if not result.get("ok"):
        _fail(f"handle_design_review failed: {result}")
    data = result["data"]
    if data.get("mode") != "ship" or "ship_gate" not in data or "challenges" not in data:
        _fail(f"ship handler payload incomplete: keys={list(data)}")
    if "coordination_evidence" not in data:
        _fail("missing coordination_evidence")
    _ok(
        f"handle_design_review(mode=ship) challenges={len(data['challenges'])} "
        f"gate={data['ship_gate']}"
    )

    review_result = asyncio.run(
        handle_design_review(
            SessionStore(),
            ScanRegistry(),
            snaps,
            {
                "snapshot_id": rec.snapshot_id,
                "mode": "review",
                "user_task": "Review dashboard",
            },
        )
    )
    if not review_result.get("ok") or "report" not in review_result.get("data", {}):
        _fail("review mode regression")
    _ok("review mode still works")

    print("ALL INSTALL VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
