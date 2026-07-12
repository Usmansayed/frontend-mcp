#!/usr/bin/env python3
"""Run Coordination Intelligence validation suite (CVW-01 .. CVW-14)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from coordination_validation.harness import ValidationHarness
from coordination_validation.workflows import all_workflow_ids, workflow_by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Coordination Intelligence validation suite")
    parser.add_argument(
        "--workflow",
        action="append",
        dest="workflows",
        help="Run specific workflow ID (repeatable). Default: all CVW workflows",
    )
    parser.add_argument(
        "--mode",
        choices=["simulate"],
        default="simulate",
        help="simulate = deterministic envelope replay through CoordinatorBridge",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "coordination" / "reports" / "latest.json",
        help="Write JSON report to this path",
    )
    parser.add_argument("--list", action="store_true", help="List workflow IDs and exit")
    args = parser.parse_args()

    if args.list:
        for wid in all_workflow_ids():
            wf = workflow_by_id(wid)
            print(f"{wid}: {wf.get('title') if wf else '?'}")
        return 0

    harness = ValidationHarness()
    ids = args.workflows or all_workflow_ids()

    if len(ids) == len(all_workflow_ids()):
        report = harness.run_all(mode=args.mode)
    else:
        workflows = [harness.run_workflow(wid, mode=args.mode) for wid in ids]
        passed = sum(1 for w in workflows if w["metrics"]["success"])
        from coordination_validation.coordination_score import build_coordination_score

        report = {
            "suite_version": "1.0.0",
            "mode": args.mode,
            "workflows": workflows,
            "summary": {
                "total": len(workflows),
                "passed": passed,
                "failed": len(workflows) - passed,
                "skipped": 0,
            },
            "coordination_score": build_coordination_score(workflows),
            "refinement_opportunities": [],
        }

    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    # Append score history for trend tracking
    score = report.get("coordination_score") or {}
    if score:
        history_path = ROOT / "evals" / "coordination" / "score_history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_entry = {
            "generated_at": report["generated_at"],
            "mode": args.mode,
            "workflows_run": len(report.get("workflows", [])),
            "summary": report.get("summary"),
            "coordination_score": score,
        }
        try:
            from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts

            history_entry["runtime_bundle_version"] = (
                load_runtime_artifacts().manifest.get("bundle_version")
            )
        except Exception:
            pass
        with history_path.open("a", encoding="utf-8") as history_file:
            history_file.write(json.dumps(history_entry) + "\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Per-workflow reports
    for wf in report.get("workflows", []):
        wf_dir = ROOT / "evals" / "coordination" / "reports" / wf["workflow_id"]
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "report.json").write_text(json.dumps(wf, indent=2), encoding="utf-8")

    summary = report.get("summary", {})
    score = report.get("coordination_score") or {}
    print(f"Coordination validation ({args.mode}): {summary.get('passed', 0)}/{summary.get('total', 0)} passed")
    if score:
        cats = score.get("categories") or {}
        compile_acc = cats.get("step_compilation_accuracy")
        compile_label = "n/a(simulate)" if compile_acc is None else f"{compile_acc:.0%}"
        print(
            f"Coordination Score: {score.get('composite', 0):.1%} composite  "
            f"(release targets {'MET' if score.get('release_targets_met') else 'NOT MET'})"
        )
        print(
            f"  cluster={cats.get('cluster_accuracy', 0):.0%}  "
            f"cap_route={cats.get('capability_routing_accuracy', 0):.0%}  "
            f"playbook={cats.get('playbook_selection_accuracy', 0):.0%}  "
            f"compile={compile_label}  "
            f"recovery={cats.get('recovery_quality', 0):.0%}  "
            f"replan={cats.get('replanning_quality', 0):.0%}  "
            f"tool_eff={cats.get('tool_efficiency', 0):.0%}  "
            f"workflow_success={cats.get('overall_workflow_success', 0):.0%}"
        )
    for wf in report.get("workflows", []):
        m = wf["metrics"]
        status = "PASS" if m["success"] else "FAIL"
        print(
            f"  {wf['workflow_id']} {status}  "
            f"cluster={m['cluster_accuracy']:.0%}  "
            f"playbook={m['playbook_accuracy']:.0%}  "
            f"cap_route={m['capability_routing_accuracy']:.0%}  "
            f"unnecessary_tools={m['unnecessary_tool_calls']}"
        )
    print(f"Report: {args.output}")

    refinements = report.get("refinement_opportunities") or []
    if refinements:
        print(f"\nRefinement opportunities ({len(refinements)}):")
        for r in refinements[:10]:
            print(f"  [{r.get('severity')}] {r.get('workflow_id')}: {r.get('description')}")

    return 0 if summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
