#!/usr/bin/env python3
"""Run Execution Validation Workflows (EVW-01 .. EVW-10)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from execution_validation.harness import ExecutionValidationHarness
from execution_validation.workflows import all_workflow_ids, workflow_by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Execution Runtime validation suite (EVW)")
    parser.add_argument(
        "--workflow",
        action="append",
        dest="workflows",
        help="Run specific workflow ID (repeatable). Default: all EVW workflows",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "execution" / "reports" / "latest.json",
        help="Write JSON report to this path",
    )
    parser.add_argument("--list", action="store_true", help="List workflow IDs and exit")
    args = parser.parse_args()

    if args.list:
        for wid in all_workflow_ids():
            wf = workflow_by_id(wid)
            print(f"{wid}: {wf.get('title') if wf else '?'}")
        return 0

    harness = ExecutionValidationHarness()
    ids = args.workflows or all_workflow_ids()

    if len(ids) == len(all_workflow_ids()):
        report = harness.run_all()
    else:
        workflows = [harness.run_workflow(wid) for wid in ids]
        passed = sum(1 for w in workflows if w["metrics"]["success"])
        from execution_validation.harness import _build_execution_score

        report = {
            "suite_version": "1.0.0",
            "workflows": workflows,
            "summary": {
                "total": len(workflows),
                "passed": passed,
                "failed": len(workflows) - passed,
            },
            "execution_score": _build_execution_score(workflows),
        }

    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for wf in report.get("workflows", []):
        wf_dir = ROOT / "evals" / "execution" / "reports" / wf["workflow_id"]
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "report.json").write_text(json.dumps(wf, indent=2), encoding="utf-8")

    summary = report.get("summary", {})
    score = report.get("execution_score") or {}
    print(f"Execution validation: {summary.get('passed', 0)}/{summary.get('total', 0)} passed")
    if score:
        print(
            f"Execution Score: {score.get('composite', 0):.1%} composite  "
            f"(release targets {'MET' if score.get('release_targets_met') else 'NOT MET'})"
        )
    for wf in report.get("workflows", []):
        m = wf["metrics"]
        status = "PASS" if m["success"] else "FAIL"
        print(f"  {wf['workflow_id']} {status}  checks={m['checks_passed']}/{m['checks_total']}")
    print(f"Report: {args.output}")

    return 0 if summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
