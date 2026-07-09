"""MCP eval — golden-path validation form playbook (AGENT_GUIDE §4)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.mcp.handlers import (
    handle_diff,
    handle_execute_actions,
    handle_execute_script,
    handle_health,
    handle_navigate,
    handle_navigate_and_observe,
    handle_observe,
    handle_probe_form,
    handle_session_end,
    handle_session_start,
    handle_verify,
)
from navigation.mcp.scan_registry import ScanRegistry
from navigation.mcp.session_store import SessionStore

PLANNING_HINT_KEYS = ("suggested_next", "next_step", "recommended_action", "you_should")


def _no_planning_hints(payload: dict) -> bool:
    text = json.dumps(payload, default=str).lower()
    return not any(k in text for k in PLANNING_HINT_KEYS)


async def main() -> int:
    parser = argparse.ArgumentParser(description="M3 validation-form eval (AGENT_GUIDE §4)")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", help="Accepted for run_all_phases compatibility.")
    args = parser.parse_args()

    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        return 1

    store = SessionStore(artifacts_root=ROOT / "artifacts" / "mcp-eval")
    scans = ScanRegistry()
    report: dict = {"suite": "mcp_eval_validation_form", "ok": False, "steps": {}}

    try:
        health = await handle_health({"url": args.url})
        report["steps"]["health"] = health["ok"] and _no_planning_hints(health)

        start = await handle_session_start(store, {"base_url": args.url, "headless": True})
        sid = start.get("session_id")
        report["steps"]["session_start"] = start["ok"] and bool(sid)

        baseline = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": "/forms/validation", "include_screenshot": True},
        )
        scan_baseline = baseline.get("scan_id")
        dom_ok = "Validated form" in str(baseline.get("data", {}).get("observation", {}).get("dom_text", ""))
        report["steps"]["observe_baseline"] = baseline["ok"] and dom_ok and _no_planning_hints(baseline)

        probe = await handle_probe_form(store, {"session_id": sid, "form": "validation"})
        report["steps"]["probe_form"] = probe["ok"] and probe.get("data", {}).get("probe", {}).get("ok")

        await handle_navigate(store, {"session_id": sid, "url": "/forms/validation"})

        invalid_act = await handle_execute_actions(
            store,
            scans,
            {
                "session_id": sid,
                "actions": [{"type": "click_button", "text": "Validate & submit"}],
                "capture_insights_during": False,
            },
        )
        report["steps"]["act_invalid"] = invalid_act["ok"]

        invalid_verify = await handle_verify(
            store,
            {"session_id": sid, "criteria": {"text_contains": ["Invalid email"]}},
        )
        report["steps"]["verify_invalid"] = (
            invalid_verify["ok"] and invalid_verify.get("data", {}).get("verified") is True
        )

        valid_act_script = await handle_execute_script(
            store,
            scans,
            {
                "session_id": sid,
                "script": "(() => { const c = document.querySelector('input[type=checkbox]'); if (c && !c.checked) c.click(); return true; })()",
                "capture_insights_during": False,
            },
        )
        valid_act = await handle_execute_actions(
            store,
            scans,
            {
                "session_id": sid,
                "actions": [
                    {"type": "set_input", "label": "Email", "value": "test@example.com"},
                    {"type": "set_input", "label": "Phone", "value": "1234567890"},
                    {"type": "set_input", "label": "Age", "value": "25"},
                    {"type": "click_button", "text": "Validate & submit"},
                ],
                "capture_insights_during": False,
            },
        )
        report["steps"]["act_valid"] = (
            valid_act_script["ok"]
            and valid_act["ok"]
            and valid_act.get("data", {}).get("actions_ok")
        )

        valid_verify = await handle_verify(
            store,
            {"session_id": sid, "criteria": {"text_contains": ["Form is valid"]}},
        )
        report["steps"]["verify_valid"] = (
            valid_verify["ok"] and valid_verify.get("data", {}).get("verified") is True
        )

        final_obs = await handle_observe(store, scans, {"session_id": sid})
        scan_final = final_obs.get("scan_id")
        blocking = final_obs.get("data", {}).get("agent_summary", {}).get("blocking") or []
        report["steps"]["final_observe"] = final_obs["ok"] and len(blocking) == 0

        if scan_baseline and scan_final:
            diff = await handle_diff(
                scans,
                {"scan_id_before": scan_baseline, "scan_id_after": scan_final},
            )
            report["steps"]["diff"] = diff["ok"] and _no_planning_hints(diff)
        else:
            report["steps"]["diff"] = False

        end = await handle_session_end(store, {"session_id": sid})
        report["steps"]["session_end"] = end["ok"]

        report["ok"] = all(report["steps"].values())
    except Exception as exc:
        report["error"] = str(exc)
        await store.end_all()

    print(f"MCP eval (validation-form): {'PASS' if report['ok'] else 'FAIL'}")
    for name, ok in report.get("steps", {}).items():
        print(f"  {name}: ok={ok}")
    if report.get("error"):
        print(f"  error: {report['error']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
