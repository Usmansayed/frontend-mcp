"""MCP contract tests — handler layer without MCP stdio (M1 + M2)."""
from __future__ import annotations

import argparse
import asyncio
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.mcp.handlers import (
    handle_auth_gate,
    handle_audit_accessibility,
    handle_audit_seo,
    handle_debug_mode,
    handle_detect_framework,
    handle_full_diagnosis,
    handle_framework_docs,
    handle_search_components,
    handle_code_context,
    handle_console_clear,
    handle_console_get,
    handle_diff,
    handle_execute_actions,
    handle_execute_script,
    handle_flow_describe,
    handle_health,
    handle_navigate,
    handle_navigate_and_observe,
    handle_network_clear,
    handle_network_get,
    handle_observe,
    handle_probe_form,
    handle_probe_guards,
    handle_session_end,
    handle_session_start,
    handle_state_list,
    handle_state_restore,
    handle_state_save,
    handle_verify,
)
from navigation.mcp.resources import list_resources, read_resource
from navigation.visual_browser_intelligence.visual.visual_response import VISUAL_ATTACHMENTS_KEY, envelope_to_mcp_contents
from navigation.core.scan_registry import ScanRegistry
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.frontend_quality_intelligence.audits.runner import lighthouse_available


async def main() -> int:
    parser = argparse.ArgumentParser(description="MCP contract tests")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", help="Accepted for run_all_phases compatibility.")
    args = parser.parse_args()

    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        return 1

    store = SessionStore(artifacts_root=ROOT / "artifacts" / "mcp")
    scans = ScanRegistry()
    report: dict = {"suite": "mcp_contract", "ok": False, "tests": {}}

    try:
        health = await handle_health({"url": args.url})
        report["tests"]["health"] = {"ok": health["ok"]}

        flows = await handle_flow_describe({})
        report["tests"]["flow_list"] = {
            "ok": flows["ok"] and "validation-form" in (flows.get("data", {}).get("flow_names") or [])
        }

        flow = await handle_flow_describe({"flow_name": "validation-form"})
        report["tests"]["flow_describe"] = {
            "ok": flow["ok"] and flow.get("data", {}).get("flow", {}).get("name") == "validation-form"
        }

        code_ctx = await handle_code_context({"repo_root": str(SANDBOX_ROOT), "query_type": "stats"})
        report["tests"]["code_context"] = {"ok": code_ctx["ok"]}

        start = await handle_session_start(store, {"base_url": args.url, "headless": True})
        report["tests"]["session_start"] = {"ok": start["ok"]}
        sid = start.get("session_id")
        if not sid:
            raise RuntimeError("no session_id")

        nav = await handle_navigate(store, {"session_id": sid, "url": "/forms/validation"})
        report["tests"]["navigate"] = {"ok": nav["ok"]}

        observe_only = await handle_observe(store, scans, {"session_id": sid})
        scan_before = observe_only.get("scan_id")
        report["tests"]["observe"] = {"ok": observe_only["ok"] and bool(scan_before)}
        observe_summary = await handle_observe(store, scans, {"session_id": sid, "detail": "summary_only"})
        report["tests"]["observe_summary_only"] = {
            "ok": observe_summary["ok"]
            and "observation" not in (observe_summary.get("data") or {})
            and bool((observe_summary.get("data") or {}).get("agent_summary"))
            and bool((observe_summary.get("data") or {}).get("visual")),
        }

        observe = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": "/forms/validation", "include_screenshot": True},
        )
        scan_after = observe.get("scan_id")
        report["tests"]["navigate_and_observe"] = {
            "ok": observe["ok"],
            "scan_id": scan_after,
            "blocking": observe.get("data", {}).get("agent_summary", {}).get("blocking", []),
            "has_visual_attachments": bool(observe.get(VISUAL_ATTACHMENTS_KEY)),
            "has_visual_insights": bool(
                (observe.get("data", {}) or {}).get("visual", {}).get("visual_insights")
            ),
        }
        report["tests"]["inline_images"] = {
            "ok": observe["ok"] and len(observe.get(VISUAL_ATTACHMENTS_KEY) or []) >= 1,
        }

        if scan_before and scan_after:
            diff = await handle_diff(
                scans,
                {"scan_id_before": scan_before, "scan_id_after": scan_after},
            )
            report["tests"]["diff"] = {"ok": diff["ok"] and "diff" in diff.get("data", {})}
            resources = list_resources(scans)
            report_uri = f"perception://scan/{scan_after}/report.json"
            screenshot_uri = f"perception://scan/{scan_after}/screenshot.png"
            annotated_uri = f"perception://scan/{scan_after}/screenshot-annotated.png"
            has_report_resource = any(r.get("uri") == report_uri for r in resources)
            report_mime, report_text, report_is_blob = read_resource(report_uri, scans)
            screenshot_ok = True
            annotated_ok = True
            if any(r.get("uri") == screenshot_uri for r in resources):
                screenshot_mime, screenshot_payload, screenshot_is_blob = read_resource(screenshot_uri, scans)
                screenshot_ok = screenshot_mime == "image/png" and screenshot_is_blob and len(screenshot_payload) > 0
            if any(r.get("uri") == annotated_uri for r in resources):
                ann_mime, ann_payload, ann_blob = read_resource(annotated_uri, scans)
                annotated_ok = ann_mime == "image/png" and ann_blob and len(ann_payload) > 0
            report["tests"]["resources_scan"] = {
                "ok": has_report_resource
                and report_mime == "application/json"
                and not report_is_blob
                and len(report_text) > 0
                and screenshot_ok
                and annotated_ok
            }
            report["tests"]["visual_diff"] = {
                "ok": diff["ok"]
                and (diff.get("data", {}) or {}).get("has_visual_diff") is True
                and bool((diff.get("data", {}) or {}).get("diff", {}).get("visual_diff")),
            }
        else:
            report["tests"]["diff"] = {"ok": False}
            report["tests"]["resources_scan"] = {"ok": False}

        gate = await handle_auth_gate(store, {"session_id": sid})
        report["tests"]["auth_gate"] = {
            "ok": gate["ok"] and gate.get("data", {}).get("requires_human") is False
        }

        verify_fail = await handle_verify(
            store,
            scans,
            {
                "session_id": sid,
                "criteria": {"text_contains": ["THIS_STRING_SHOULD_NOT_EXIST_MCP_TEST"]},
            },
        )
        report["tests"]["verify_negative"] = {
            "ok": verify_fail["ok"]
            and verify_fail.get("data", {}).get("verified") is False
            and bool(verify_fail.get("data", {}).get("failure_scan_id"))
            and bool(verify_fail.get(VISUAL_ATTACHMENTS_KEY)),
        }

        verify_ok = await handle_verify(
            store,
            scans,
            {
                "session_id": sid,
                "criteria": {
                    "url_contains": ["/forms/validation"],
                    "text_contains": ["Validated form"],
                },
            },
        )
        report["tests"]["verify_positive"] = {
            "ok": verify_ok["ok"] and verify_ok.get("data", {}).get("verified") is True
        }

        execute = await handle_execute_script(
            store,
            scans,
            {
                "session_id": sid,
                "script": "(() => document.title)()",
                "capture_insights_during": False,
            },
        )
        report["tests"]["execute_script"] = {
            "ok": execute["ok"] and execute.get("data", {}).get("script_ok"),
            "scan_after": execute.get("scan_id"),
        }

        await handle_navigate(store, {"session_id": sid, "url": "/forms/validation"})
        actions = await handle_execute_actions(
            store,
            scans,
            {
                "session_id": sid,
                "actions": [{"type": "click_button", "text": "Validate & submit"}],
                "capture_insights_during": False,
            },
        )
        # Click without fill triggers validation errors — action succeeds, form shows errors
        report["tests"]["execute_actions"] = {"ok": actions["ok"]}

        form = await handle_probe_form(store, {"session_id": sid, "form": "validation"})
        report["tests"]["probe_form"] = {"ok": form["ok"]}

        guards = await handle_probe_guards(store, {"session_id": sid, "mode": "maze"})
        report["tests"]["probe_guards"] = {"ok": guards["ok"]}

        saved = await handle_state_save(store, {"session_id": sid, "state_id": "mcp-test"})
        listed = await handle_state_list(store, {"session_id": sid})
        report["tests"]["state_save_list"] = {
            "ok": saved["ok"] and listed["ok"] and "mcp-test" in (listed.get("data", {}).get("states") or [])
        }

        await handle_navigate(store, {"session_id": sid, "url": "/"})
        restored = await handle_state_restore(store, {"session_id": sid, "state_id": "mcp-test"})
        report["tests"]["state_restore"] = {"ok": restored["ok"]}

        devtest = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": "/edge-lab?devtest=1", "include_screenshot": False},
        )
        obs_console = ((devtest.get("data") or {}).get("observation") or {}).get("console") or {}
        entries = obs_console.get("entries") or []
        has_console_error = any("EDGE_LAB_CONSOLE_ERROR" in str(e.get("text", "")) for e in entries)
        agent_console = (devtest.get("data") or {}).get("agent_summary", {}).get("console") or {}
        report["tests"]["console_observe"] = {
            "ok": devtest["ok"] and has_console_error and agent_console.get("by_level", {}).get("error", 0) >= 1,
        }

        await handle_execute_script(
            store,
            scans,
            {
                "session_id": sid,
                "script": (
                    "(() => { console.log('MCP_CONSOLE_TEST_LOG'); "
                    "console.info('MCP_CONSOLE_TEST_INFO'); "
                    "console.debug('MCP_CONSOLE_TEST_DEBUG'); return true; })()"
                ),
                "capture_insights_during": False,
            },
        )
        console_get = await handle_console_get(
            store,
            {"session_id": sid, "contains": "MCP_CONSOLE_TEST", "limit": 20},
        )
        get_entries = (console_get.get("data") or {}).get("console", {}).get("entries") or []
        levels = {e.get("level") for e in get_entries}
        report["tests"]["console_get_filter"] = {
            "ok": console_get["ok"]
            and "MCP_CONSOLE_TEST_LOG" in str(get_entries)
            and {"log", "info", "debug"}.issubset(levels),
        }

        cleared = await handle_console_clear(store, {"session_id": sid})
        after_clear = await handle_console_get(store, {"session_id": sid})
        report["tests"]["console_clear"] = {
            "ok": cleared["ok"]
            and (after_clear.get("data") or {}).get("console", {}).get("session_total", 1) == 0,
        }

        net_devtest = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": "/edge-lab?devtest=1", "include_screenshot": False},
        )
        net_scan_id = net_devtest.get("scan_id")
        obs_network = ((net_devtest.get("data") or {}).get("observation") or {}).get("network") or {}
        has_404 = any(
            "dev-insights-missing" in str(e.get("url", ""))
            for e in (obs_network.get("failures") or []) + (obs_network.get("entries") or [])
        )
        agent_network = (net_devtest.get("data") or {}).get("agent_summary", {}).get("network") or {}
        report["tests"]["network_observe_failure"] = {
            "ok": net_devtest["ok"] and has_404 and agent_network.get("failed_count", 0) >= 1,
        }

        net_slow_observe = await handle_navigate_and_observe(
            store,
            scans,
            {"session_id": sid, "url": "/edge-lab?devtestb=1", "include_screenshot": False},
        )
        slow_network = ((net_slow_observe.get("data") or {}).get("observation") or {}).get("network") or {}
        has_slow = slow_network.get("slow_count", 0) >= 1 or any(
            "dev-insights-slow" in str(s.get("url", "")) for s in slow_network.get("slow_requests") or []
        )
        report["tests"]["network_observe_slow"] = {"ok": net_slow_observe["ok"] and has_slow}

        net_get = await handle_network_get(
            store,
            {"session_id": sid, "api_group": "dev-insights-ok", "limit": 20},
        )
        net_entries = (net_get.get("data") or {}).get("network", {}).get("entries") or []
        report["tests"]["network_get_filter"] = {
            "ok": net_get["ok"] and any("dev-insights-ok" in str(e.get("url", "")) for e in net_entries),
        }

        if net_scan_id:
            har_uri = f"perception://scan/{net_scan_id}/network.har"
            resources = list_resources(scans)
            has_har = any(r.get("uri") == har_uri for r in resources)
            har_mime, har_text, har_blob = read_resource(har_uri, scans)
            report["tests"]["network_har_resource"] = {
                "ok": has_har
                and har_mime == "application/json"
                and not har_blob
                and '"version": "1.2"' in har_text,
            }
        else:
            report["tests"]["network_har_resource"] = {"ok": False}

        net_cleared = await handle_network_clear(store, {"session_id": sid})
        after_net_clear = await handle_network_get(store, {"session_id": sid})
        report["tests"]["network_clear"] = {
            "ok": net_cleared["ok"]
            and (after_net_clear.get("data") or {}).get("network", {}).get("session_total", 1) == 0,
        }

        if lighthouse_available():
            await handle_navigate(store, {"session_id": sid, "url": "/forms/validation"})
            a11y = await handle_audit_accessibility(
                store,
                {"session_id": sid, "url": "/forms/validation", "timeout_s": 120},
            )
            audit = (a11y.get("data") or {}).get("audit") or {}
            report["tests"]["audit_accessibility"] = {
                "ok": a11y["ok"]
                and audit.get("category") == "accessibility"
                and isinstance(audit.get("score"), (int, float))
                and audit.get("score", 0) > 0
                and bool(audit.get("artifacts", {}).get("lighthouse_json")),
            }

            seo = await handle_audit_seo(
                store,
                {"session_id": sid, "url": "/forms/validation", "timeout_s": 120},
            )
            seo_audit = (seo.get("data") or {}).get("audit") or {}
            report["tests"]["audit_seo"] = {
                "ok": seo["ok"]
                and seo_audit.get("category") == "seo"
                and isinstance(seo_audit.get("score"), (int, float)),
            }
        else:
            report["tests"]["audit_accessibility"] = {"ok": True, "skipped": True}
            report["tests"]["audit_seo"] = {"ok": True, "skipped": True}

        debug = await handle_debug_mode(
            store,
            scans,
            {"session_id": sid, "url": "/forms/validation", "include_screenshot": False},
        )
        dbg_report = (debug.get("data") or {}).get("perception_report") or {}
        dbg_summary = (debug.get("data") or {}).get("agent_summary") or {}
        report["tests"]["diagnosis_debug_mode"] = {
            "ok": debug["ok"]
            and dbg_report.get("mode") == "debug"
            and bool(debug.get("scan_id"))
            and dbg_report.get("console") is not None
            and dbg_report.get("network") is not None
            and "diagnosis" in dbg_summary,
        }

        full_no_audits = await handle_full_diagnosis(
            store,
            scans,
            {
                "session_id": sid,
                "url": "/forms/validation",
                "include_screenshot": False,
                "run_audits": False,
            },
        )
        full_report = (full_no_audits.get("data") or {}).get("perception_report") or {}
        report["tests"]["diagnosis_full_no_audits"] = {
            "ok": full_no_audits["ok"]
            and full_report.get("mode") == "full"
            and full_report.get("verification", {}).get("ok") is True
            and not full_report.get("audits"),
        }

        diag_scan_id = debug.get("scan_id")
        if diag_scan_id:
            diag_uri = f"perception://scan/{diag_scan_id}/diagnosis.json"
            resources = list_resources(scans)
            has_diag = any(r.get("uri") == diag_uri for r in resources)
            diag_mime, diag_text, diag_blob = read_resource(diag_uri, scans)
            report["tests"]["diagnosis_resource"] = {
                "ok": has_diag
                and diag_mime == "application/json"
                and not diag_blob
                and '"mode": "debug"' in diag_text,
            }
        else:
            report["tests"]["diagnosis_resource"] = {"ok": False}

        detect_fw = await handle_detect_framework({"repo_root": str(SANDBOX_ROOT)})
        fw_meta = (detect_fw.get("data") or {}).get("metadata") or {}
        report["tests"]["detect_framework"] = {
            "ok": detect_fw["ok"]
            and fw_meta.get("framework") == "React"
            and fw_meta.get("build_tool") == "Vite"
            and fw_meta.get("package_manager") == "npm",
        }

        fw_docs = await handle_framework_docs(
            {
                "repo_root": str(SANDBOX_ROOT),
                "topic": "React Router nested routes",
                "use_cache": True,
            },
        )
        knowledge = (fw_docs.get("data") or {}).get("framework_knowledge") or {}
        has_content = bool(str(knowledge.get("content") or "").strip())
        degraded = knowledge.get("degraded") or fw_docs.get("degraded") or []
        degraded_text = " ".join(str(item) for item in degraded)
        docs_graceful = any(
            token in degraded_text
            for token in (
                "docs_provider_unavailable",
                "grounded_docs_cli_unavailable",
                "node_version_too_old",
                "library_spec_not_found",
                "library_not_indexed",
                "docs_empty_result",
                "grounded_docs_timeout",
            )
        )
        report["tests"]["framework_docs"] = {
            "ok": fw_docs["ok"] or docs_graceful,
            "has_content": has_content,
            "cached": knowledge.get("cached", False),
        }

        comp_search = await handle_search_components({"query": "modern login form"})
        search_data = (comp_search.get("data") or {}).get("component_search") or {}
        candidates = search_data.get("candidates") or []
        search_degraded = search_data.get("degraded") or comp_search.get("degraded") or []
        search_degraded_text = " ".join(str(item) for item in search_degraded)
        search_graceful = "shadcn_ecosystem_unavailable" in search_degraded_text or "registries_index_unavailable" in search_degraded_text
        report["tests"]["search_components"] = {
            "ok": comp_search["ok"] or search_graceful,
            "total": len(candidates),
        }

        end = await handle_session_end(store, {"session_id": sid})
        report["tests"]["session_end"] = {"ok": end["ok"]}

        report["ok"] = all(t.get("ok") for t in report["tests"].values())
    except Exception as exc:
        report["error"] = str(exc)
        await store.end_all()

    print(f"MCP contract: {'PASS' if report['ok'] else 'FAIL'}")
    for name, result in report.get("tests", {}).items():
        print(f"  {name}: ok={result.get('ok')}")
    if report.get("error"):
        print(f"  error: {report['error']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
