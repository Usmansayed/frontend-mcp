"""Soak / reliability test scaffold (Wave 4 / R1–R4).

R1: 50 rounds of observe → verify on the same session.
Emits ``artifacts/performance/soak.json`` with memory hints and per-iteration timings.

This is a scaffold — memory tracing uses ``tracemalloc`` where available.
Marked ``slow``; not part of the fast tier.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import tracemalloc

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_navigate_and_observe,
    handle_observe,
    handle_session_end,
    handle_session_start,
    handle_verify,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


async def main() -> int:
    parser = argparse.ArgumentParser(description="MCP soak test — observe/verify loop")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--route", default="/")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        return 1

    tracemalloc.start()
    store = SessionStore(artifacts_root=ROOT / "artifacts" / "soak")
    scans = ScanRegistry()

    start = await handle_session_start(store, {"base_url": args.url, "headless": True})
    sid = start.get("session_id")
    if not sid:
        return 1

    iterations: list[dict] = []
    started = time.monotonic()
    try:
        await handle_navigate_and_observe(
            store, scans, {"session_id": sid, "url": args.route, "include_screenshot": False}
        )
        for i in range(args.iterations):
            t_obs = time.monotonic()
            obs = await handle_observe(store, scans, {"session_id": sid, "detail": "summary_only"})
            obs_ms = (time.monotonic() - t_obs) * 1000
            t_ver = time.monotonic()
            ver = await handle_verify(
                store,
                {"session_id": sid, "criteria": {"url_contains": ["/"]}},
            )
            ver_ms = (time.monotonic() - t_ver) * 1000
            current, peak = tracemalloc.get_traced_memory()
            iterations.append({
                "i": i,
                "observe_ms": round(obs_ms, 1),
                "verify_ms": round(ver_ms, 1),
                "verify_ok": (ver.get("data") or {}).get("verified") is True,
                "observe_ok": obs["ok"],
                "current_mem_kb": current // 1024,
                "peak_mem_kb": peak // 1024,
            })
    finally:
        await handle_session_end(store, {"session_id": sid})
        await store.end_all()

    total_ms = int((time.monotonic() - started) * 1000)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    verify_pass = sum(1 for it in iterations if it["verify_ok"])
    observe_pass = sum(1 for it in iterations if it["observe_ok"])
    report = {
        "suite": "soak_r1",
        "iterations": len(iterations),
        "total_ms": total_ms,
        "final_mem_kb": current // 1024,
        "peak_mem_kb": peak // 1024,
        "observe_pass": observe_pass,
        "verify_pass": verify_pass,
        "ok": observe_pass == len(iterations) and verify_pass == len(iterations),
        "detail": iterations,
    }

    out_dir = ROOT / "artifacts" / "performance"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "soak.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Soak R1: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"  iterations: {len(iterations)}, total: {total_ms}ms, peak mem: {peak // 1024}KB")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
