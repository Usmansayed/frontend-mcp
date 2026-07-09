"""Phase 1: observation + verification + form probe + auth gate."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from dotenv import load_dotenv

from navigation.perception import (
    artifact_dir,
    check_auth_gate,
    collect_observation,
    dump_json,
    probe_tier_a_dev_insights,
    probe_tier_b_dev_insights,
    probe_validation_form,
)

load_dotenv(ROOT / ".env")
load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1: observation + verification")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    try:
        from browser_use import BrowserProfile, BrowserSession
    except ImportError:
        print("browser-use not installed")
        return 1

    out = artifact_dir("phase1", ROOT / "artifacts" / "phase1")
    images = out / "images"
    report: dict = {"phase": 1, "ok": False, "tests": {}}
    obs_ok = False
    probe_ok = False
    dev_a_ok = False
    dev_b_ok = False

    session = BrowserSession(browser_profile=BrowserProfile(headless=args.headless))
    try:
        await session.start()
        await session.navigate_to(args.url)

        # 1. Auth gate on login
        await session.navigate_to(f"{args.url.rstrip('/')}/login")
        gate = await check_auth_gate(session)
        report["tests"]["auth_gate_login"] = gate.to_dict()
        gate_ok = gate.requires_human

        # 2. Observation on validation form (includes dev_insights collector if errors occur)
        await session.navigate_to(f"{args.url.rstrip('/')}/forms/validation")
        obs = await collect_observation(session, images_dir=images, name="validation-form")
        dump_json(out / "observation.json", obs.to_dict())
        obs_ok = bool(obs.url and obs.dom_text and obs.screenshot_path)

        # 3. Form probe
        probe = await probe_validation_form(session, args.url)
        report["tests"]["form_probe"] = probe.to_dict()
        probe_ok = probe.ok

        # 4. Tier A dev insights (console errors, exceptions, failed network)
        dev_a = await probe_tier_a_dev_insights(session, args.url)
        report["tests"]["dev_insights_tier_a"] = dev_a
        dump_json(out / "dev_insights_tier_a.json", dev_a.get("insights", {}))
        dev_a_ok = dev_a.get("ok", False)

        # 5. Tier B dev insights (warnings, API calls, slow requests, UI errors, page meta)
        dev_b = await probe_tier_b_dev_insights(session, args.url)
        report["tests"]["dev_insights_tier_b"] = dev_b
        dump_json(out / "dev_insights_tier_b.json", dev_b.get("insights", {}))
        dev_b_ok = dev_b.get("ok", False)

        report["ok"] = gate_ok and obs_ok and probe_ok and dev_a_ok and dev_b_ok
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            await session.kill()
        except Exception:
            pass

    dump_json(out / "report.json", report)
    dump_json(ROOT / "artifacts" / "phase1" / "report.json", report)

    print(f"Phase 1: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"  auth_gate:      {report['tests'].get('auth_gate_login', {})}")
    print(f"  observation:    ok={obs_ok}")
    print(f"  form_probe:     ok={probe_ok}")
    print(f"  dev_insights A: ok={dev_a_ok}")
    print(f"  dev_insights B: ok={dev_b_ok}")
    print(f"  artifacts:      {out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        sys.exit(1)
    raise SystemExit(asyncio.run(main()))
