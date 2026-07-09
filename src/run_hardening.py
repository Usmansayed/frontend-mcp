"""Hardening checks: nested CDP collectors, unified scan, cookie restore."""
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
    probe_nested_collectors,
    scan_page,
)

load_dotenv(ROOT / ".env")
load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Hardening: hub, scan, cookies")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    from browser_use import BrowserProfile, BrowserSession

    out = artifact_dir("hardening", ROOT / "artifacts" / "hardening")
    report: dict = {"suite": "hardening", "ok": False, "tests": {}}

    session = BrowserSession(browser_profile=BrowserProfile(headless=args.headless))
    mgr = StateManager()
    try:
        await session.start()

        nested = await probe_nested_collectors(session, args.url)
        report["tests"]["nested_collectors"] = nested

        scan = await scan_page(
            session,
            f"{args.url.rstrip('/')}/forms/validation",
            images_dir=out / "images",
            name="validation-scan",
        )
        report["tests"]["scan_page"] = scan.to_dict()
        scan_ok = scan.ok and scan.observation is not None and bool(scan.observation.url)

        await session.navigate_to(args.url)
        cdp = await session.get_or_create_cdp_session(target_id=None, focus=True)
        await cdp.cdp_client.send.Network.setCookie(
            params={
                "name": "fpe_cookie_test",
                "value": "hardening",
                "domain": "localhost",
                "path": "/",
            },
            session_id=cdp.session_id,
        )
        snap = await mgr.snapshot(session, "cookie_test")
        await cdp.cdp_client.send.Network.clearBrowserCookies(session_id=cdp.session_id)
        before = await mgr._get_cookies(session)
        restored = await mgr.restore(session, snap.state_id)
        after = await mgr._get_cookies(session)
        cookie_ok = (
            restored
            and not any(c.get("name") == "fpe_cookie_test" for c in before)
            and any(c.get("name") == "fpe_cookie_test" and c.get("value") == "hardening" for c in after)
        )
        report["tests"]["cookie_restore"] = {
            "ok": cookie_ok,
            "restored": restored,
            "cookies_after": len(after),
        }

        report["ok"] = nested.get("ok") and scan_ok and cookie_ok
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            await session.kill()
        except Exception:
            pass

    dump_json(out / "report.json", report)
    dump_json(ROOT / "artifacts" / "hardening" / "report.json", report)

    print(f"Hardening: {'PASS' if report['ok'] else 'FAIL'}")
    for name, result in report.get("tests", {}).items():
        ok = result.get("ok") if isinstance(result, dict) else result
        print(f"  {name}: ok={ok}")
    print(f"  artifacts: {out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        sys.exit(1)
    raise SystemExit(asyncio.run(main()))
