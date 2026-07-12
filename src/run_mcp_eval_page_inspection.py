"""MCP eval E2E-2 — page inspection playbook (AGENT_GUIDE §2).

Reference: docs/PRODUCTION_TEST_PLAN.md and evals/PAGE_INSPECTION_EVAL.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.mcp.handlers import (
    handle_diff,
    handle_health,
    handle_navigate_and_observe,
    handle_observe,
    handle_session_end,
    handle_session_start,
    handle_verify,
)
from navigation.core.scan_registry import ScanRegistry
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

PLANNING_HINT_KEYS = ("suggested_next", "next_step", "recommended_action", "you_should")

SCENARIO_ID = "E2E-2"
ARTIFACT_DIR = ROOT / "artifacts" / "evals" / SCENARIO_ID


def _no_planning_hints(payload: dict) -> bool:
    text = json.dumps(payload, default=str).lower()
    return not any(k in text for k in PLANNING_HINT_KEYS)


def _record(report: dict, step: str, ok: bool, **details: object) -> None:
    report["steps"][step] = {"ok": ok, **details}
    report["trace"].append({"step": step, "ok": ok, **details})


async def main() -> int:
    parser = argparse.ArgumentParser(description=f"MCP eval {SCENARIO_ID} — page inspection")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--route", default="/", help="Route to inspect")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        return 1

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    store = SessionStore(artifacts_root=ROOT / "artifacts" / "mcp-eval")
    scans = ScanRegistry()
    started = time.monotonic()
    report: dict = {
        "suite": f"mcp_eval_{SCENARIO_ID.lower()}",
        "scenario_id": SCENARIO_ID,
        "route": args.route,
        "ok": False,
        "steps": {},
        "trace": [],
    }

    try:
        health = await handle_health({"url": args.url})
        _record(report, "health", bool(health["ok"] and _no_planning_hints(health)))

        start = await handle_session_start(store, {"base_url": args.url, "headless": True})
        sid = start.get("session_id")
        _record(report, "session_start", start["ok"] and bool(sid))
        if not sid:
            raise RuntimeError("no session_id from session_start")

        first = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": args.route, "include_screenshot": True},
        )
        scan_before = first.get("scan_id")
        data = first.get("data") or {}
        agent_summary = data.get("agent_summary") or {}
        blocking = list(agent_summary.get("blocking") or [])
        page_meta = agent_summary.get("page_meta") or {}
        _record(
            report,
            "navigate_and_observe",
            first["ok"] and bool(scan_before) and _no_planning_hints(first),
            scan_id=scan_before,
            title=page_meta.get("title"),
            blocking_count=len(blocking),
        )

        verify = await handle_verify(
            store,
            {
                "session_id": sid,
                "criteria": {"url_contains": [args.route.rstrip("/") or "/"]},
            },
        )
        verified = (verify.get("data") or {}).get("verified") is True
        _record(report, "verify", verify["ok"] and verified, verified=verified)

        second = await handle_observe(store, scans, {"session_id": sid})
        scan_after = second.get("scan_id")
        blocking_after = list(((second.get("data") or {}).get("agent_summary") or {}).get("blocking") or [])
        _record(
            report,
            "observe_second",
            second["ok"] and bool(scan_after),
            scan_id=scan_after,
            blocking_count=len(blocking_after),
        )

        diff = None
        if scan_before and scan_after:
            diff = await handle_diff(
                scans,
                {"scan_id_before": scan_before, "scan_id_after": scan_after},
            )
            _record(
                report,
                "diff",
                diff["ok"] and _no_planning_hints(diff),
            )
        else:
            _record(report, "diff", False)

        end = await handle_session_end(store, {"session_id": sid})
        _record(report, "session_end", end["ok"])

        report["final"] = {
            "verified": verified,
            "blocking": blocking_after,
            "no_planning_hints": _no_planning_hints(first) and _no_planning_hints(verify),
        }
        report["ok"] = all(step["ok"] for step in report["steps"].values()) and not blocking_after
    except Exception as exc:
        report["error"] = str(exc)
        await store.end_all()

    report["duration_ms"] = int((time.monotonic() - started) * 1000)
    (ARTIFACT_DIR / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"MCP eval {SCENARIO_ID}: {'PASS' if report['ok'] else 'FAIL'}")
    for name, result in report.get("steps", {}).items():
        print(f"  {name}: ok={result.get('ok')}")
    if report.get("error"):
        print(f"  error: {report['error']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
