"""Performance baseline for MCP handlers (Wave 4 / gate G10).

Measures p50/p95 latency for the tools with declared budgets in
``docs/PRODUCTION_TEST_PLAN.md``:

- ``perception_observe`` (summary_only)
- ``perception_navigate_and_observe`` (full + screenshot)
- ``perception_full_diagnosis`` (with audits disabled to avoid Lighthouse)

Runs against a live sandbox at ``--url``. Emits
``artifacts/performance/baseline.json`` with per-tool timings and a
``regressed_vs_budget`` list.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_full_diagnosis,
    handle_navigate_and_observe,
    handle_observe,
    handle_session_end,
    handle_session_start,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


BUDGETS_MS = {
    "observe_summary_only": 8_000,
    "navigate_and_observe_full": 15_000,
    "full_diagnosis_no_audits": 180_000,
}


async def _time(fn, *args, **kwargs) -> tuple[dict, float]:
    started = time.monotonic()
    result = await fn(*args, **kwargs)
    return result, (time.monotonic() - started) * 1000.0


def _stats(samples: list[float]) -> dict:
    if not samples:
        return {"count": 0}
    sorted_s = sorted(samples)
    p95_idx = max(0, int(round(0.95 * (len(sorted_s) - 1))))
    return {
        "count": len(samples),
        "min_ms": round(min(samples), 1),
        "p50_ms": round(statistics.median(samples), 1),
        "p95_ms": round(sorted_s[p95_idx], 1),
        "max_ms": round(max(samples), 1),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="MCP performance baseline")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--route", default="/forms/validation")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        return 1

    store = SessionStore(artifacts_root=ROOT / "artifacts" / "perf")
    scans = ScanRegistry()

    start_env, _ = await _time(handle_session_start, store, {"base_url": args.url, "headless": True})
    sid = start_env.get("session_id")
    if not sid:
        print("failed to start session")
        return 1

    timings: dict[str, list[float]] = {
        "observe_summary_only": [],
        "navigate_and_observe_full": [],
        "full_diagnosis_no_audits": [],
    }

    try:
        for _ in range(args.iterations):
            _res, ms = await _time(
                handle_navigate_and_observe,
                store,
                scans,
                {"session_id": sid, "url": args.route, "include_screenshot": True},
            )
            timings["navigate_and_observe_full"].append(ms)

            _res, ms = await _time(
                handle_observe,
                store,
                scans,
                {"session_id": sid, "detail": "summary_only"},
            )
            timings["observe_summary_only"].append(ms)

            _res, ms = await _time(
                handle_full_diagnosis,
                store,
                scans,
                {
                    "session_id": sid,
                    "url": args.route,
                    "include_screenshot": False,
                    "run_audits": False,
                },
            )
            timings["full_diagnosis_no_audits"].append(ms)
    finally:
        await handle_session_end(store, {"session_id": sid})
        await store.end_all()

    report = {
        "suite": "performance_baseline",
        "url": args.url,
        "route": args.route,
        "iterations": args.iterations,
        "timings": {name: _stats(samples) for name, samples in timings.items()},
        "budgets_ms": BUDGETS_MS,
    }
    regressed = []
    for tool, budget in BUDGETS_MS.items():
        p95 = report["timings"].get(tool, {}).get("p95_ms")
        if p95 is not None and p95 > budget:
            regressed.append({"tool": tool, "p95_ms": p95, "budget_ms": budget})
    report["regressed_vs_budget"] = regressed
    report["ok"] = not regressed

    out_dir = ROOT / "artifacts" / "performance"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Performance baseline: {'PASS' if report['ok'] else 'FAIL'}")
    for tool, stats in report["timings"].items():
        budget = BUDGETS_MS.get(tool)
        print(f"  {tool}: p50={stats.get('p50_ms')}ms p95={stats.get('p95_ms')}ms budget={budget}ms")
    for row in regressed:
        print(f"  REGRESSION: {row}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
