#!/usr/bin/env python3
"""Production validation gate — CVW + EVW + pytest suites + release gate + benchmarks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _architecture_scorecard(
    cvw: dict | None,
    evw: dict | None,
    pytest_ok: bool,
    contract_ok: bool,
) -> dict:
    cvw_score = (cvw or {}).get("coordination_score") or {}
    evw_score = (evw or {}).get("execution_score") or {}
    cvw_composite = cvw_score.get("composite", 0.0)
    evw_composite = evw_score.get("composite", 0.0)
    infra_ok = pytest_ok and contract_ok
    composite = 0.4 * cvw_composite + 0.3 * evw_composite + (0.3 if infra_ok else 0.0)
    return {
        "composite": round(composite, 4),
        "coordination_layer": {
            "status": "frozen_v1.0.0",
            "cvw_composite": cvw_composite,
            "cvw_passed": (cvw or {}).get("summary", {}).get("failed", 1) == 0,
        },
        "execution_runtime": {
            "status": "production_ready" if evw_score.get("release_targets_met") else "in_progress",
            "evw_composite": evw_composite,
            "evw_passed": (evw or {}).get("summary", {}).get("failed", 1) == 0,
        },
        "infrastructure_tests": {
            "pytest_ok": pytest_ok,
            "mcp_contract_ok": contract_ok,
        },
    }


def _production_readiness(
    *,
    cvw_ok: bool,
    evw_ok: bool,
    pytest_ok: bool,
    contract_ok: bool,
    release_ok: bool,
    perf_ok: bool,
    scorecard: dict,
) -> dict:
    blockers: list[str] = []
    recommendations: list[str] = []

    if not cvw_ok:
        blockers.append("CVW coordination validation failed — coordination layer regression")
    if not evw_ok:
        blockers.append("EVW execution validation failed — runtime policies not production-grade")
    if not pytest_ok:
        blockers.append("Unit/integration pytest suite failed")
    if not contract_ok:
        blockers.append("MCP contract tests failed")
    if not release_ok:
        blockers.append("Production release gate G1–G10 not fully met")
    if not perf_ok:
        recommendations.append("Run performance baseline and record artifacts/performance/baseline.json")

    ready = not blockers and scorecard.get("composite", 0) >= 0.95
    version = "1.0.0" if ready else None

    return {
        "production_ready": ready,
        "version": version,
        "frozen": ready,
        "blockers": blockers,
        "recommendations": recommendations,
        "scorecard": scorecard,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Full production validation suite")
    parser.add_argument("--skip-cvw", action="store_true")
    parser.add_argument("--skip-evw", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-contract", action="store_true")
    parser.add_argument("--skip-release", action="store_true")
    parser.add_argument("--skip-perf", action="store_true")
    args = parser.parse_args()

    results: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "suites": {}}

    # CVW
    cvw_report = None
    if not args.skip_cvw:
        code, out = _run([sys.executable, str(ROOT / "src" / "run_coordination_validation.py")])
        cvw_report = _load_json(ROOT / "evals" / "coordination" / "reports" / "latest.json")
        results["suites"]["cvw"] = {"ok": code == 0, "exit_code": code, "output_tail": out[-2000:]}
    else:
        cvw_report = _load_json(ROOT / "evals" / "coordination" / "reports" / "latest.json")
        results["suites"]["cvw"] = {"ok": True, "skipped": True}

    # EVW
    evw_report = None
    if not args.skip_evw:
        code, out = _run([sys.executable, str(ROOT / "src" / "run_execution_validation.py")])
        evw_report = _load_json(ROOT / "evals" / "execution" / "reports" / "latest.json")
        results["suites"]["evw"] = {"ok": code == 0, "exit_code": code, "output_tail": out[-2000:]}
    else:
        evw_report = _load_json(ROOT / "evals" / "execution" / "reports" / "latest.json")
        results["suites"]["evw"] = {"ok": True, "skipped": True}

    # Execution runtime unit tests
    pytest_ok = True
    if not args.skip_pytest:
        code, out = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_execution_runtime.py",
                "tests/test_execution_runtime_e2_e4.py",
                "-m",
                "unit",
                "-q",
            ],
        )
        pytest_ok = code == 0
        results["suites"]["execution_runtime_tests"] = {
            "ok": pytest_ok,
            "exit_code": code,
            "output_tail": out[-2000:],
        }

    # MCP contract
    contract_ok = True
    if not args.skip_contract:
        code, out = _run([sys.executable, str(ROOT / "src" / "run_mcp_contract_tests.py")])
        contract_ok = code == 0
        results["suites"]["mcp_contract"] = {
            "ok": contract_ok,
            "exit_code": code,
            "output_tail": out[-2000:],
        }

    # Release gate
    release_ok = True
    if not args.skip_release:
        code, out = _run([sys.executable, str(ROOT / "src" / "run_release_gate.py")])
        release_ok = code == 0
        results["suites"]["release_gate"] = {
            "ok": release_ok,
            "exit_code": code,
            "output_tail": out[-2000:],
        }

    # Performance baseline
    perf_ok = True
    if not args.skip_perf:
        baseline = ROOT / "artifacts" / "performance" / "baseline.json"
        if baseline.exists():
            perf_data = _load_json(baseline)
            perf_ok = not (perf_data or {}).get("regressed_vs_budget")
            results["suites"]["performance"] = {"ok": perf_ok, "source": str(baseline)}
        else:
            code, out = _run([sys.executable, str(ROOT / "src" / "run_performance_baseline.py")])
            perf_ok = code == 0
            results["suites"]["performance"] = {
                "ok": perf_ok,
                "exit_code": code,
                "output_tail": out[-2000:],
            }

    cvw_ok = (cvw_report or {}).get("summary", {}).get("failed", 1) == 0
    evw_ok = (evw_report or {}).get("summary", {}).get("failed", 1) == 0

    scorecard = _architecture_scorecard(cvw_report, evw_report, pytest_ok, contract_ok)
    readiness = _production_readiness(
        cvw_ok=cvw_ok,
        evw_ok=evw_ok,
        pytest_ok=pytest_ok,
        contract_ok=contract_ok,
        release_ok=release_ok,
        perf_ok=perf_ok,
        scorecard=scorecard,
    )

    results["architecture_scorecard"] = scorecard
    results["production_readiness"] = readiness
    results["ok"] = readiness["production_ready"]

    out_dir = ROOT / "evals" / "production"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "readiness_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("=== Production Validation ===")
    for name, suite in results["suites"].items():
        status = "PASS" if suite.get("ok") else "FAIL"
        print(f"  {name}: {status}")
    print(f"\nArchitecture scorecard composite: {scorecard['composite']:.1%}")
    print(f"Production ready: {readiness['production_ready']}")
    if readiness.get("version"):
        print(f"Platform version: v{readiness['version']} (FROZEN)")
    if readiness["blockers"]:
        print("\nBlockers:")
        for b in readiness["blockers"]:
            print(f"  - {b}")
    if readiness["recommendations"]:
        print("\nRecommendations:")
        for r in readiness["recommendations"]:
            print(f"  - {r}")
    print(f"\nReport: {report_path}")

    return 0 if results["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
