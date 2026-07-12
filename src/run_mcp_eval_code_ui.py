"""MCP eval E2E-10 — code ↔ live UI correlation (AGENT_GUIDE §10).

Playbook:
1. `perception_code_context` on the sandbox repo — get repo stats and a route lookup.
2. `perception_navigate_and_observe` on the same route in the running app.
3. Cross-check that the observed page's <title> or DOM references the same feature the
   code stats surface (loose check — module list is non-empty and observation succeeded).

Reference: docs/PRODUCTION_TEST_PLAN.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.mcp.handlers import (
    handle_code_context,
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

SCENARIO_ID = "E2E-10"
ARTIFACT_DIR = ROOT / "artifacts" / "evals" / SCENARIO_ID


def _no_planning_hints(payload: dict) -> bool:
    text = json.dumps(payload, default=str).lower()
    return not any(k in text for k in PLANNING_HINT_KEYS)


def _record(report: dict, step: str, ok: bool, **details: object) -> None:
    report["steps"][step] = {"ok": ok, **details}
    report["trace"].append({"step": step, "ok": ok, **details})


async def main() -> int:
    parser = argparse.ArgumentParser(description=f"MCP eval {SCENARIO_ID} — code ↔ UI correlation")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--route", default="/forms/validation")
    parser.add_argument("--repo-root", default=str(SANDBOX_ROOT))
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
        _record(report, "health", bool(health["ok"]))

        stats = await handle_code_context({"repo_root": args.repo_root, "query_type": "stats"})
        stats_ok = stats["ok"] and bool((stats.get("data") or {}).get("stats"))
        _record(report, "code_context_stats", stats_ok)

        route_lookup = await handle_code_context(
            {"repo_root": args.repo_root, "query_type": "get_route", "route": args.route}
        )
        route_data = (route_lookup.get("data") or {}).get("route") or {}
        route_files = route_data.get("files") or route_data.get("candidates") or []
        _record(
            report,
            "code_context_get_route",
            route_lookup["ok"] or bool(route_lookup.get("degraded")),
            route_files_count=len(route_files),
        )

        start = await handle_session_start(store, {"base_url": args.url, "headless": True})
        sid = start.get("session_id")
        _record(report, "session_start", start["ok"] and bool(sid))
        if not sid:
            raise RuntimeError("no session_id")

        obs = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": args.route, "include_screenshot": False},
        )
        dom_text = str(((obs.get("data") or {}).get("observation") or {}).get("dom_text") or "")
        _record(
            report,
            "navigate_and_observe",
            obs["ok"] and _no_planning_hints(obs),
            dom_text_len=len(dom_text),
        )

        verify = await handle_verify(
            store,
            {"session_id": sid, "criteria": {"url_contains": [args.route]}},
        )
        _record(report, "verify_route", verify["ok"] and (verify.get("data") or {}).get("verified") is True)

        second = await handle_observe(store, scans, {"session_id": sid, "detail": "summary_only"})
        blocking = list(((second.get("data") or {}).get("agent_summary") or {}).get("blocking") or [])
        _record(report, "final_observe", second["ok"] and not blocking, blocking_count=len(blocking))

        end = await handle_session_end(store, {"session_id": sid})
        _record(report, "session_end", end["ok"])

        report["final"] = {
            "code_stats_ok": stats_ok,
            "route_files_found": len(route_files),
            "ui_reachable": obs["ok"],
            "blocking": blocking,
        }
        report["ok"] = all(step["ok"] for step in report["steps"].values())
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
