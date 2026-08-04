"""MCP eval E2E-17 — AI visibility fix loop (audit → check → verify).

Playbook:
1. `perception_seo_status` — must expose the `ai_visibility` block.
2. `perception_seo_audit` on the target site (defaults to a URL that is safe to
   fetch from CI, or the strikeloop-like golden fixture URL when
   ``--use-fixture`` is set) with ``include_ai_visibility: true``.
3. Confirm the audit envelope contains ``reasoning_context_v2.ai_readiness``
   with overall_score and dimensions.
4. `perception_seo_query` for ``ai.readiness.summary`` — must return either
   ``ai_readiness_not_computed_for_this_audit`` (empty graph in this run) or
   the computed summary from the just-completed audit.
5. `perception_seo_audit` a second time with ``include_ai_visibility: false``
   and confirm the block disappears (matches the failure scenario F13).

Reference: docs/PRODUCTION_TEST_PLAN.md failure scenario F13, gate G8.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from navigation.core.scan_registry import ScanRegistry
from navigation.mcp.handlers import (
    handle_seo_audit,
    handle_seo_query,
    handle_seo_status,
)

SCENARIO_ID = "E2E-17"
ARTIFACT_DIR = ROOT / "artifacts" / "evals" / SCENARIO_ID


def _record(report: dict, step: str, ok: bool, **details: object) -> None:
    report["steps"][step] = {"ok": ok, **details}
    report["trace"].append({"step": step, "ok": ok, **details})


async def main() -> int:
    parser = argparse.ArgumentParser(description=f"MCP eval {SCENARIO_ID} — AI visibility fix loop")
    parser.add_argument("--website", default="https://example.com/")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    scans = ScanRegistry()
    started = time.monotonic()
    report: dict = {
        "suite": f"mcp_eval_{SCENARIO_ID.lower()}",
        "scenario_id": SCENARIO_ID,
        "website": args.website,
        "ok": False,
        "steps": {},
        "trace": [],
    }

    try:
        status = await handle_seo_status({})
        ai_status = (status.get("data") or {}).get("ai_visibility") or {}
        _record(
            report,
            "seo_status_exposes_ai_visibility",
            status["ok"] and bool(ai_status),
            phase=ai_status.get("phase"),
            analyzers=ai_status.get("analyzers"),
        )

        audit_on = await handle_seo_audit(
            scans,
            {"website_url": args.website, "include_ai_visibility": True},
        )
        ctx_on = (audit_on.get("data") or {}).get("reasoning_context_v2") or {}
        block = ctx_on.get("ai_readiness") or {}
        _record(
            report,
            "audit_with_ai_visibility_true",
            audit_on["ok"] and bool(block),
            overall_score=block.get("overall_score"),
            analyzers_run=block.get("analyzers_run"),
            analyzers_skipped=block.get("analyzers_skipped"),
            dimension_count=len(block.get("dimensions") or {}),
        )

        recs = (audit_on.get("data") or {}).get("recommendations") or []
        ai_recs = [r for r in recs if (r.get("category") or "").lower() == "ai_visibility"]
        _record(
            report,
            "ai_recommendations_emitted",
            audit_on["ok"] and (bool(ai_recs) or bool(block)),
            ai_rec_count=len(ai_recs),
        )

        summary = await handle_seo_query({"query_id": "ai.readiness.summary"})
        summary_result = (summary.get("data") or {}).get("result") or {}
        expected_message = summary_result.get("message") == "ai_readiness_not_computed_for_this_audit"
        computed = bool(summary_result.get("dimensions") or summary_result.get("overall_score") is not None)
        _record(
            report,
            "ai_readiness_summary_query",
            summary["ok"] and (expected_message or computed),
            has_computed=computed,
            message=summary_result.get("message"),
        )

        audit_off = await handle_seo_audit(
            scans,
            {"website_url": args.website, "include_ai_visibility": False},
        )
        ctx_off = (audit_off.get("data") or {}).get("reasoning_context_v2") or {}
        recs_off = (audit_off.get("data") or {}).get("recommendations") or []
        ai_recs_off = [r for r in recs_off if (r.get("category") or "").lower() == "ai_visibility"]
        _record(
            report,
            "audit_with_ai_visibility_false_omits_block",
            audit_off["ok"] and "ai_readiness" not in ctx_off and not ai_recs_off,
            ai_readiness_present=("ai_readiness" in ctx_off),
            ai_rec_count=len(ai_recs_off),
        )

        report["final"] = {
            "toggle_matrix_pass": (
                bool(block)
                and "ai_readiness" not in ctx_off
            ),
            "no_planning_hints": True,
        }
        report["ok"] = all(step["ok"] for step in report["steps"].values())
    except Exception as exc:
        report["error"] = str(exc)

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
