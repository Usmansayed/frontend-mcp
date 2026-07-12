"""Execution Runtime E2–E4 tests — reliability, idempotency, observability."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import CompiledStep
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.execution_runtime import (
    CancellationToken,
    ExecutionPolicies,
    FailureClass,
    RetryDecision,
    SafeToolRegistry,
    classify_failure,
    evaluate_retry,
)
from navigation.execution_runtime.policies.config import FailureInjector
from navigation.execution_runtime.runtime import ExecutionRuntime
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


@pytest.fixture
def policies() -> ExecutionPolicies:
    return ExecutionPolicies()


@pytest.fixture
def runtime(policies: ExecutionPolicies) -> ExecutionRuntime:
    return ExecutionRuntime(
        SessionStore(),
        ScanRegistry(),
        SnapshotRegistry(),
        policies=policies,
    )


@pytest.mark.unit
def test_classify_failure_permanent_unknown_tool() -> None:
    fc = classify_failure(
        tool="perception_x",
        envelope={"ok": False, "error": "unknown tool: perception_x", "data": {}},
    )
    assert fc == FailureClass.PERMANENT


@pytest.mark.unit
def test_classify_failure_transient() -> None:
    fc = classify_failure(
        tool="perception_health",
        envelope={"ok": False, "error": "connection refused", "data": {}},
    )
    assert fc == FailureClass.TRANSIENT


@pytest.mark.unit
def test_evaluate_retry_safe_tool_transient() -> None:
    registry = SafeToolRegistry()
    decision = evaluate_retry(
        tool="perception_flow_describe",
        failure_class=FailureClass.TRANSIENT,
        attempt=1,
        policy=ExecutionPolicies().retry,
        safe_registry=registry,
    )
    assert decision == RetryDecision.RETRY


@pytest.mark.unit
def test_evaluate_retry_mutating_no_retry() -> None:
    registry = SafeToolRegistry()
    decision = evaluate_retry(
        tool="perception_verify",
        failure_class=FailureClass.TRANSIENT,
        attempt=1,
        policy=ExecutionPolicies().retry,
        safe_registry=registry,
    )
    assert decision == RetryDecision.ABORT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotency_dedupes_safe_tool(runtime: ExecutionRuntime) -> None:
    args = {"flow_id": "checkout"}
    first = await runtime.execute_tool("perception_flow_describe", args)
    second = await runtime.execute_tool("perception_flow_describe", args)
    assert not first.replayed
    assert second.replayed
    assert second.ok
    exec_meta = (second.envelope.get("data") or {}).get("execution") or {}
    assert exec_meta.get("replayed") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mutating_tool_not_deduped(runtime: ExecutionRuntime) -> None:
    args = {"session_id": "idem-test"}
    first = await runtime.execute_tool("perception_verify", args)
    second = await runtime.execute_tool("perception_verify", args)
    assert not first.replayed
    assert not second.replayed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failure_injection_retry_then_success(policies: ExecutionPolicies) -> None:
    policies.failure_injector = FailureInjector(
        rules={"perception_flow_describe": ["transient"]},
    )
    rt = ExecutionRuntime(
        SessionStore(),
        ScanRegistry(),
        SnapshotRegistry(),
        policies=policies,
    )
    result = await rt.execute_tool("perception_flow_describe", {"flow_id": "checkout"})
    assert result.ok
    assert result.attempt >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_permanent_failure_single_attempt(policies: ExecutionPolicies) -> None:
    policies.failure_injector = FailureInjector(
        rules={"perception_flow_describe": ["permanent", "permanent"]},
    )
    rt = ExecutionRuntime(
        SessionStore(),
        ScanRegistry(),
        SnapshotRegistry(),
        policies=policies,
    )
    result = await rt.execute_tool("perception_flow_describe", {"flow_id": "checkout"})
    assert not result.ok
    assert result.attempt == 1
    assert result.failure_class == FailureClass.PERMANENT.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancellation_aborts(policies: ExecutionPolicies) -> None:
    policies.cancellation = CancellationToken()
    policies.cancellation.cancel()
    rt = ExecutionRuntime(
        SessionStore(),
        ScanRegistry(),
        SnapshotRegistry(),
        policies=policies,
    )
    result = await rt.execute_tool("perception_flow_describe", {"flow_id": "checkout"})
    assert result.cancelled
    assert not result.ok


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execution_metadata_on_envelope(runtime: ExecutionRuntime) -> None:
    result = await runtime.execute_tool("perception_flow_describe", {"flow_id": "checkout"})
    data = (result.envelope.get("data") or {}).get("execution") or {}
    assert data.get("execution_id")
    assert data.get("correlation_id")
    assert data.get("tool") == "perception_flow_describe"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_correlation_id_shared_in_compiled_step(runtime: ExecutionRuntime) -> None:
    step = CompiledStep(
        capability_id="test",
        semantic_action="test",
        step_id=None,
        tools=[
            {"tool": "perception_flow_describe", "arguments": {"flow_id": "checkout"}},
            {"tool": "perception_code_context", "arguments": {"repo_root": str(ROOT)}},
        ],
        playbook_id=None,
    )
    batch = await runtime.execute(step)
    corr_ids = {r.correlation_id for r in batch.results}
    assert len(corr_ids) == 1
    assert batch.correlation_id in corr_ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_and_metrics_recorded(runtime: ExecutionRuntime) -> None:
    await runtime.execute_tool("perception_flow_describe", {"flow_id": "checkout"})
    assert runtime.trace is not None
    assert len(runtime.trace.events) >= 1
    assert runtime.metrics is not None
    assert runtime.metrics.total_calls >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recovery_hint_on_verify_failure(policies: ExecutionPolicies) -> None:
    policies.failure_injector = FailureInjector(
        rules={"perception_verify": ["permanent"]},
    )
    rt = ExecutionRuntime(
        SessionStore(),
        ScanRegistry(),
        SnapshotRegistry(),
        policies=policies,
    )
    result = await rt.execute_tool("perception_verify", {"session_id": "rec-test"})
    assert result.recovery_trigger == "TR_VERIFY_FAIL"
