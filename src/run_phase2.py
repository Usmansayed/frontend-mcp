"""Phase 2: state manager + route guards."""
from __future__ import annotations

import argparse
import asyncio
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from dotenv import load_dotenv

from navigation.perception import (
    StateManager,
    artifact_dir,
    dump_json,
    probe_maze_guards,
)
from navigation.design_workflow_intelligence.state.route_guards import login_as_admin
from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url

load_dotenv(ROOT / ".env")
load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2: state + route guards")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    from browser_use import BrowserProfile, BrowserSession

    out = artifact_dir("phase2", ROOT / "artifacts" / "phase2")
    report: dict = {"phase": 2, "ok": False, "tests": {}}

    session = BrowserSession(browser_profile=BrowserProfile(headless=args.headless))
    mgr = StateManager()
    try:
        await session.start()

        # 1. localStorage roundtrip
        await session.navigate_to(args.url)
        await evaluate_js(session, "localStorage.setItem('fpe_test', 'phase2')")
        snap = await mgr.snapshot(session, "storage_test")
        await evaluate_js(session, "localStorage.clear()")
        cleared = await evaluate_js(session, "localStorage.getItem('fpe_test')")
        restored = await mgr.restore(session, snap.state_id)
        after = await evaluate_js(session, "localStorage.getItem('fpe_test')")
        storage_ok = cleared is None and restored and after == "phase2"
        report["tests"]["storage_roundtrip"] = {
            "ok": storage_ok,
            "snapshot": snap.to_dict(),
        }

        # 2. logged_in state label (metadata for coding agents)
        await login_as_admin(session, args.url)
        url_after_login = await read_current_url(session)
        logged_snap = await mgr.snapshot(session, "logged_in")
        logged_ok = "/dashboard" in url_after_login
        report["tests"]["logged_in_snapshot"] = {
            "ok": logged_ok,
            "state_id": logged_snap.state_id,
            "url": logged_snap.url,
        }

        # 3. Route guards (in-app nav after login — no full reload)
        guards = await probe_maze_guards(session, args.url)
        report["tests"]["route_guards"] = guards.to_dict()
        dump_json(out / "guards.json", guards.to_dict())

        report["ok"] = storage_ok and logged_ok and guards.ok
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            await session.kill()
        except Exception:
            pass

    dump_json(out / "report.json", report)
    dump_json(ROOT / "artifacts" / "phase2" / "report.json", report)

    print(f"Phase 2: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"  artifacts: {out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        sys.exit(1)
    raise SystemExit(asyncio.run(main()))
