"""Production polish evaluation — measures v1.1.1 handler changes vs v1.1.0 baseline."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_integrate_component,
    handle_navigate_and_observe,
    handle_observe,
    handle_probe_guards,
    handle_search_components,
    handle_seo_audit_start,
    handle_session_end,
    handle_session_start,
)
from navigation.mcp.resources import list_resources, read_resource
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


def _payload_bytes(obj: dict) -> int:
    return len(json.dumps(obj, separators=(",", ":")).encode("utf-8"))


async def _timed(coro) -> tuple[dict, float]:
    started = time.monotonic()
    result = await coro
    return result, (time.monotonic() - started) * 1000.0


async def main() -> int:
    parser = argparse.ArgumentParser(description="v1.1.1 polish evaluation")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    report: dict = {
        "suite": "v1.1.1_polish_eval",
        "url": args.url,
        "repo_root": str(SANDBOX_ROOT),
        "tests": {},
        "timings_ms": {},
        "payload_bytes": {},
        "ok": True,
    }

    # --- MCP static resources (no browser) ---
    static_uris = [
        "perception://agent-guide",
        "perception://resolver-guide",
        "perception://seo-guide",
    ]
    resource_results = {}
    for uri in static_uris:
        try:
            mime, text, is_blob = read_resource(uri)
            resource_results[uri] = {
                "ok": mime == "text/markdown" and not is_blob and len(text) > 500,
                "mime": mime,
                "chars": len(text),
            }
        except Exception as exc:
            resource_results[uri] = {"ok": False, "error": str(exc)}
    report["tests"]["mcp_static_resources"] = resource_results

    # --- Component search (cold + warm) ---
    search_cold, ms_cold = await _timed(handle_search_components({"query": "date picker"}))
    report["timings_ms"]["search_components_cold"] = round(ms_cold, 1)
    search_warm, ms_warm = await _timed(handle_search_components({"query": "date picker"}))
    report["timings_ms"]["search_components_warm"] = round(ms_warm, 1)
    report["tests"]["search_components"] = {
        "ok": search_cold.get("ok") is True,
        "candidate_count": len(
            ((search_cold.get("data") or {}).get("component_search") or {}).get("candidates") or []
        ),
        "cold_ms": round(ms_cold, 1),
        "warm_ms": round(ms_warm, 1),
        "target_met_warm": ms_warm < 2000,
    }
    report["payload_bytes"]["search_components"] = _payload_bytes(search_cold)

    # --- Component integrate (plan_only default) ---
    integrate, ms_int = await _timed(
        handle_integrate_component(
            {
                "query": "modern login form",
                "repo_root": str(SANDBOX_ROOT),
                "plan_only": True,
            }
        )
    )
    report["timings_ms"]["integrate_component_plan_only"] = round(ms_int, 1)
    report["tests"]["integrate_component"] = {
        "ok": integrate.get("ok") is True,
        "timeout": ms_int >= 5000,
        "partial": bool((integrate.get("data") or {}).get("partial")),
        "plan_only_default": True,
        "latency_ms": round(ms_int, 1),
        "target_met": ms_int < 5000 and integrate.get("ok") is True,
        "has_install_commands": bool(
            (
                ((integrate.get("data") or {}).get("integration_result") or {})
                .get("integration", {})
                .get("installation_plan", {})
                .get("install_commands")
            )
            or (
                ((integrate.get("data") or {}).get("integration_result") or {})
                .get("integration", {})
            )
        ),
    }
    report["payload_bytes"]["integrate_component"] = _payload_bytes(integrate)

    if not SANDBOX_ROOT.exists():
        report["tests"]["browser_skipped"] = "sandbox missing"
        out = ROOT / "artifacts" / "evals" / "v1.1.1_polish_eval.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    store = SessionStore(artifacts_root=ROOT / "artifacts" / "polish_eval")
    scans = ScanRegistry()

    start, ms_start = await _timed(
        handle_session_start(store, {"base_url": args.url, "headless": args.headless})
    )
    sid = start.get("session_id")
    report["timings_ms"]["session_start"] = round(ms_start, 1)
    if not sid:
        report["ok"] = False
        report["tests"]["session_start"] = {"ok": False, "error": start.get("error")}
        out = ROOT / "artifacts" / "evals" / "v1.1.1_polish_eval.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

    try:
        url_before_probe = args.url.rstrip("/") + "/forms/validation"
        nav, ms_nav = await _timed(
            handle_navigate_and_observe(
                store,
                scans,
                {"session_id": sid, "url": "/forms/validation"},
            )
        )
        scan_id = nav.get("scan_id") or (nav.get("data") or {}).get("scan_id")
        report["timings_ms"]["navigate_and_observe_default"] = round(ms_nav, 1)
        report["payload_bytes"]["navigate_and_observe_default"] = _payload_bytes(nav)
        report["tests"]["navigate_and_observe_default"] = {
            "ok": nav.get("ok") is True,
            "detail": (nav.get("data") or {}).get("detail"),
            "has_dom": "observation" in (nav.get("data") or {}),
            "latency_ms": round(ms_nav, 1),
        }

        nav_meta, ms_meta = await _timed(
            handle_navigate_and_observe(
                store,
                scans,
                {"session_id": sid, "url": "/forms/validation", "detail": "metadata_only"},
            )
        )
        report["timings_ms"]["navigate_and_observe_metadata_only"] = round(ms_meta, 1)
        report["payload_bytes"]["navigate_and_observe_metadata_only"] = _payload_bytes(nav_meta)
        report["tests"]["payload_metadata_only"] = {
            "ok": nav_meta.get("ok") is True,
            "has_dom": "observation" in (nav_meta.get("data") or {}),
            "has_visual": "visual" in (nav_meta.get("data") or {}),
            "bytes": _payload_bytes(nav_meta),
            "reduction_vs_default": round(
                100
                * (
                    1
                    - _payload_bytes(nav_meta)
                    / max(1, _payload_bytes(nav))
                ),
                1,
            ),
        }

        observe_sum, ms_obs = await _timed(
            handle_observe(store, scans, {"session_id": sid, "detail": "summary_only"})
        )
        report["timings_ms"]["observe_summary_only"] = round(ms_obs, 1)
        report["payload_bytes"]["observe_summary_only"] = _payload_bytes(observe_sum)

        guards, ms_guards = await _timed(
            handle_probe_guards(store, {"session_id": sid, "mode": "maze", "restore_session": True})
        )
        report["timings_ms"]["probe_guards_maze"] = round(ms_guards, 1)
        hygiene = (guards.get("data") or {}).get("session_hygiene") or {}
        report["tests"]["probe_guards_session_hygiene"] = {
            "ok": guards.get("ok") is True,
            "restored": hygiene.get("restored"),
            "url_before": hygiene.get("url_before"),
            "url_after": hygiene.get("url_after"),
            "degraded": guards.get("degraded") or [],
        }

        if scan_id:
            seo_dev, ms_seo = await _timed(
                handle_seo_audit_start(
                    scans,
                    {
                        "website_url": args.url,
                        "scan_id": scan_id,
                        "repo_root": str(SANDBOX_ROOT),
                    },
                )
            )
            report["timings_ms"]["seo_audit_start_development"] = round(ms_seo, 1)
            data = seo_dev.get("data") or {}
            report["tests"]["seo_development_instant"] = {
                "ok": seo_dev.get("ok") is True,
                "status": data.get("status"),
                "instant": data.get("instant"),
                "terminal": data.get("terminal"),
                "audit_id": data.get("audit_id"),
                "latency_ms": round(ms_seo, 1),
                "target_met": ms_seo < 2000 and data.get("status") == "completed",
            }
            report["payload_bytes"]["seo_audit_start_development"] = _payload_bytes(seo_dev)

            seo_pro, ms_pro = await _timed(
                handle_seo_audit_start(
                    scans,
                    {
                        "website_url": args.url,
                        "mode": "professional",
                        "scan_id": scan_id,
                        "repo_root": str(SANDBOX_ROOT),
                    },
                )
            )
            report["timings_ms"]["seo_audit_start_professional_enqueue"] = round(ms_pro, 1)
            pdata = seo_pro.get("data") or {}
            report["tests"]["seo_professional_async"] = {
                "ok": seo_pro.get("ok") is True or seo_pro.get("error") == "auth_required",
                "error": seo_pro.get("error"),
                "audit_job_id": pdata.get("audit_job_id"),
                "instant": pdata.get("instant"),
                "auth_blocked": seo_pro.get("error") == "auth_required",
            }
    finally:
        await handle_session_end(store, {"session_id": sid})
        await store.end_all()

    # Aggregate pass/fail
    critical = [
        report["tests"].get("integrate_component", {}).get("target_met"),
        report["tests"].get("probe_guards_session_hygiene", {}).get("restored"),
        all(v.get("ok") for v in resource_results.values()),
    ]
    report["ok"] = all(x is not False for x in critical if x is not None)

    out = ROOT / "artifacts" / "evals" / "v1.1.1_polish_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
