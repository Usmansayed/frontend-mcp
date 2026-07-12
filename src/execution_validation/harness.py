"""Execution validation harness — EVW workflows through ExecutionRuntime."""

from __future__ import annotations

import time
from typing import Any

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.execution_runtime.policies.config import ExecutionPolicies, FailureInjector
from navigation.execution_runtime.runtime import ExecutionRuntime
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

from execution_validation.workflows import load_workflows, workflow_by_id


class ExecutionValidationHarness:
    """Run EVW workflows deterministically with stubbed or live handlers."""

    def __init__(self) -> None:
        pass

    def _build_runtime(self, workflow: dict[str, Any]) -> ExecutionRuntime:
        policies = ExecutionPolicies()
        injection = workflow.get("failure_injection")
        if injection:
            policies.failure_injector = FailureInjector(rules=dict(injection))
        if workflow.get("cancel_before"):
            policies.cancellation.cancel()
        return ExecutionRuntime(
            SessionStore(),
            ScanRegistry(),
            SnapshotRegistry(),
            policies=policies,
        )

    def run_all(self) -> dict[str, Any]:
        workflows = load_workflows().get("workflows", [])
        results = [self.run_workflow(wf["workflow_id"]) for wf in workflows]
        passed = sum(1 for r in results if r["metrics"]["success"])
        n = len(results)
        return {
            "suite_version": "1.0.0",
            "workflows": results,
            "summary": {
                "total": n,
                "passed": passed,
                "failed": n - passed,
            },
            "execution_score": _build_execution_score(results),
        }

    def run_workflow(self, workflow_id: str) -> dict[str, Any]:
        wf = workflow_by_id(workflow_id)
        if not wf:
            raise KeyError(f"Unknown workflow: {workflow_id}")

        start = time.perf_counter()
        runtime = self._build_runtime(wf)
        checks: list[dict[str, Any]] = []
        success = True

        if wf.get("compiled_step"):
            batch = _run_sync(runtime.execute(wf["compiled_step"]))
            checks.extend(_check_compiled(wf, batch, runtime))
        else:
            for step in wf.get("steps") or []:
                result = _run_sync(
                    runtime.execute_tool(step["tool"], step.get("arguments") or {})
                )
                checks.extend(_check_step(step, result, runtime))

        if wf.get("expect_metrics"):
            checks.extend(_check_metrics(wf["expect_metrics"], runtime))

        success = all(c["passed"] for c in checks)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return {
            "workflow_id": workflow_id,
            "title": wf.get("title"),
            "metrics": {
                "success": success,
                "elapsed_ms": elapsed_ms,
                "checks_passed": sum(1 for c in checks if c["passed"]),
                "checks_total": len(checks),
            },
            "checks": checks,
            "trace": runtime.trace.to_dict() if runtime.trace else None,
            "metrics_snapshot": runtime.metrics.to_dict() if runtime.metrics else None,
        }


def _run_sync(coro: Any) -> Any:
    import asyncio

    return asyncio.run(coro)


def _check_step(
    step: dict[str, Any],
    result: Any,
    runtime: ExecutionRuntime,
) -> list[dict[str, Any]]:
    expect = step.get("expect") or {}
    checks: list[dict[str, Any]] = []

    if "ok" in expect:
        ok = result.ok == expect["ok"]
        checks.append({"name": "ok", "passed": ok, "expected": expect["ok"], "actual": result.ok})

    if "replayed" in expect:
        passed = result.replayed == expect["replayed"]
        checks.append({
            "name": "replayed",
            "passed": passed,
            "expected": expect["replayed"],
            "actual": result.replayed,
        })

    if "failure_class" in expect:
        passed = result.failure_class == expect["failure_class"]
        checks.append({
            "name": "failure_class",
            "passed": passed,
            "expected": expect["failure_class"],
            "actual": result.failure_class,
        })

    if "max_attempts" in expect:
        passed = result.attempt <= expect["max_attempts"]
        checks.append({
            "name": "max_attempts",
            "passed": passed,
            "expected": f"<= {expect['max_attempts']}",
            "actual": result.attempt,
        })

    if "min_attempts" in expect:
        passed = result.attempt >= expect["min_attempts"]
        checks.append({
            "name": "min_attempts",
            "passed": passed,
            "expected": f">= {expect['min_attempts']}",
            "actual": result.attempt,
        })

    if expect.get("has_execution_metadata"):
        data = (result.envelope.get("data") or {}).get("execution")
        passed = isinstance(data, dict) and "execution_id" in data
        checks.append({
            "name": "has_execution_metadata",
            "passed": passed,
            "expected": True,
            "actual": bool(data),
        })

    if "recovery_trigger" in expect:
        passed = result.recovery_trigger == expect["recovery_trigger"]
        checks.append({
            "name": "recovery_trigger",
            "passed": passed,
            "expected": expect["recovery_trigger"],
            "actual": result.recovery_trigger,
        })

    if expect.get("cancelled"):
        passed = result.cancelled or result.failure_class == "cancelled"
        checks.append({
            "name": "cancelled",
            "passed": passed,
            "expected": True,
            "actual": result.cancelled,
        })

    return checks


def _check_compiled(
    wf: dict[str, Any],
    batch: Any,
    runtime: ExecutionRuntime,
) -> list[dict[str, Any]]:
    expect = wf.get("expect") or {}
    checks: list[dict[str, Any]] = []

    if "ok" in expect:
        checks.append({
            "name": "compiled_ok",
            "passed": batch.ok == expect["ok"],
            "expected": expect["ok"],
            "actual": batch.ok,
        })

    if "max_results" in expect:
        passed = len(batch.results) <= expect["max_results"]
        checks.append({
            "name": "max_results",
            "passed": passed,
            "expected": f"<= {expect['max_results']}",
            "actual": len(batch.results),
        })

    if "min_results" in expect:
        passed = len(batch.results) >= expect["min_results"]
        checks.append({
            "name": "min_results",
            "passed": passed,
            "expected": f">= {expect['min_results']}",
            "actual": len(batch.results),
        })

    if expect.get("shared_correlation"):
        corr_ids = {r.correlation_id for r in batch.results}
        passed = len(corr_ids) == 1 and batch.correlation_id is not None
        checks.append({
            "name": "shared_correlation",
            "passed": passed,
            "expected": True,
            "actual": list(corr_ids),
        })

    return checks


def _check_metrics(expect: dict[str, Any], runtime: ExecutionRuntime) -> list[dict[str, Any]]:
    metrics = runtime.metrics
    checks: list[dict[str, Any]] = []
    if metrics is None:
        return [{"name": "metrics_present", "passed": False, "expected": True, "actual": None}]

    if "total_calls_min" in expect:
        passed = metrics.total_calls >= expect["total_calls_min"]
        checks.append({
            "name": "total_calls_min",
            "passed": passed,
            "expected": expect["total_calls_min"],
            "actual": metrics.total_calls,
        })
    return checks


def _build_execution_score(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results)
    passed = sum(1 for r in results if r["metrics"]["success"])
    workflow_success = passed / max(n, 1)
    total_checks = sum(r["metrics"]["checks_total"] for r in results)
    passed_checks = sum(r["metrics"]["checks_passed"] for r in results)
    check_accuracy = passed_checks / max(total_checks, 1)
    composite = 0.6 * workflow_success + 0.4 * check_accuracy
    return {
        "composite": round(composite, 4),
        "workflow_success_rate": round(workflow_success, 4),
        "check_accuracy": round(check_accuracy, 4),
        "release_targets_met": workflow_success >= 1.0 and check_accuracy >= 0.95,
        "categories": {
            "workflow_success": round(workflow_success, 4),
            "check_accuracy": round(check_accuracy, 4),
            "idempotency": _category_rate(results, "EVW-01"),
            "retry_policy": _category_rate(results, "EVW-02"),
            "failure_classification": _category_rate(results, "EVW-03"),
            "observability": _category_rate(results, ["EVW-05", "EVW-06", "EVW-09"]),
            "cancellation": _category_rate(results, "EVW-07"),
            "recovery": _category_rate(results, "EVW-08"),
        },
    }


def _category_rate(
    results: list[dict[str, Any]],
    workflow_ids: str | list[str],
) -> float:
    ids = {workflow_ids} if isinstance(workflow_ids, str) else set(workflow_ids)
    subset = [r for r in results if r["workflow_id"] in ids]
    if not subset:
        return 1.0
    return sum(1 for r in subset if r["metrics"]["success"]) / len(subset)
