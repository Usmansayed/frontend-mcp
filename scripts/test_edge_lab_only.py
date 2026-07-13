"""Run only the 3 edge-lab contract tests against installed PyPI package."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from importlib.metadata import version

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_navigate_and_observe,
    handle_session_end,
    handle_session_start,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

URL = "http://localhost:5173"


async def main() -> int:
    print(f"frontend-perception-engine {version('frontend-perception-engine')}")
    print(f"frontend-mcp {version('frontend-mcp')}")

    root = Path(tempfile.mkdtemp(prefix="edge-lab-test-"))
    store = SessionStore(artifacts_root=root / "artifacts")
    scans = ScanRegistry()
    results: dict[str, dict] = {}
    sid: str | None = None

    try:
        start = await handle_session_start(store, {"base_url": URL, "headless": True})
        if not start.get("ok"):
            print(json.dumps({"error": "session_start failed", "start": start}, indent=2))
            return 1
        sid = start["session_id"]

        devtest = await handle_navigate_and_observe(
            store,
            scans,
            {
                "session_id": sid,
                "url": "/edge-lab?devtest=1",
                "include_screenshot": False,
                "detail": "full",
            },
        )
        obs = (devtest.get("data") or {}).get("observation") or {}
        console = obs.get("console") or {}
        entries = console.get("entries") or []
        has_console = any("EDGE_LAB_CONSOLE_ERROR" in str(e.get("text", "")) for e in entries)
        agent_console = (devtest.get("data") or {}).get("agent_summary", {}).get("console") or {}
        results["console_observe"] = {
            "ok": devtest["ok"] and has_console and agent_console.get("by_level", {}).get("error", 0) >= 1,
            "has_console_error": has_console,
            "error_count": agent_console.get("by_level", {}).get("error", 0),
        }

        network = obs.get("network") or {}
        has_404 = any(
            "dev-insights-missing" in str(e.get("url", ""))
            for e in (network.get("failures") or []) + (network.get("entries") or [])
        )
        agent_net = (devtest.get("data") or {}).get("agent_summary", {}).get("network") or {}
        results["network_observe_failure"] = {
            "ok": devtest["ok"] and has_404 and agent_net.get("failed_count", 0) >= 1,
            "has_404": has_404,
            "failed_count": agent_net.get("failed_count", 0),
        }

        slow_obs = await handle_navigate_and_observe(
            store,
            scans,
            {
                "session_id": sid,
                "url": "/edge-lab?devtestb=1",
                "include_screenshot": False,
                "detail": "full",
            },
        )
        slow_net = ((slow_obs.get("data") or {}).get("observation") or {}).get("network") or {}
        has_slow = slow_net.get("slow_count", 0) >= 1 or any(
            "dev-insights-slow" in str(s.get("url", "")) for s in slow_net.get("slow_requests") or []
        )
        results["network_observe_slow"] = {
            "ok": slow_obs["ok"] and has_slow,
            "has_slow": has_slow,
            "slow_count": slow_net.get("slow_count", 0),
        }

        all_ok = all(r["ok"] for r in results.values())
        print(json.dumps({"all_ok": all_ok, "tests": results}, indent=2))
        return 0 if all_ok else 1
    finally:
        if sid:
            try:
                await handle_session_end(store, {"session_id": sid})
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
