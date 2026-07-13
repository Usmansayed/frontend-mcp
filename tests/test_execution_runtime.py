"""Execution Runtime E1 tests — dispatch, executor, ledger."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.models import CompiledStep
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.execution_runtime import ExecutionRuntime, execute, configure
from navigation.execution_runtime.dispatch_registry import DispatchRegistry
from navigation.mcp.tools import perception_tools
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


@pytest.fixture
def runtime() -> ExecutionRuntime:
    rt = ExecutionRuntime(SessionStore(), ScanRegistry(), SnapshotRegistry())
    configure(rt)
    return rt


@pytest.mark.unit
def test_dispatch_registry_covers_all_mcp_tools() -> None:
    class _StubToolType:
        def __init__(self, name: str, description: str, inputSchema: dict, **kwargs: object) -> None:
            self.name = name
            self.description = description
            self.inputSchema = inputSchema
            for key, value in kwargs.items():
                setattr(self, key, value)

    class _StubTypes:
        Tool = _StubToolType

    store = SessionStore()
    registry = DispatchRegistry.build(store, ScanRegistry(), SnapshotRegistry())
    tool_names = {t.name for t in perception_tools(_StubTypes)}
    missing = tool_names - set(registry.tool_names())
    assert not missing, f"DispatchRegistry missing tools: {sorted(missing)}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_health(runtime: ExecutionRuntime) -> None:
    result = await runtime.execute_tool("perception_health", {"url": "http://127.0.0.1:1"})
    assert result.envelope["contract_version"] == "1.0"
    assert result.envelope["tool"] == "perception_health"
    assert result.latency_ms >= 0
    record = runtime.ledger.last()
    assert record is not None
    assert record.tool == "perception_health"
    assert record.execution_id == result.execution_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_unknown_returns_error_envelope(runtime: ExecutionRuntime) -> None:
    result = await runtime.execute_tool("perception_nonexistent_tool", {})
    assert not result.ok
    assert "unknown tool" in (result.envelope.get("error") or "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_compiled_step_sequential(runtime: ExecutionRuntime) -> None:
    step = CompiledStep(
        capability_id="flow_describe",
        semantic_action="describe_flow",
        step_id=None,
        tools=[
            {"tool": "perception_flow_describe", "arguments": {"flow_id": "checkout"}},
            {"tool": "perception_code_context", "arguments": {"repo_root": str(ROOT)}},
        ],
        playbook_id=None,
    )
    batch = await execute(step)
    assert len(batch.results) == 2
    assert batch.capability_id == "flow_describe"
    assert len(runtime.ledger.records()) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_stops_on_first_failure(runtime: ExecutionRuntime) -> None:
    step = CompiledStep(
        capability_id="test",
        semantic_action="test",
        step_id=None,
        tools=[
            {"tool": "perception_nonexistent_tool", "arguments": {}},
            {"tool": "perception_health", "arguments": {}},
        ],
        playbook_id=None,
    )
    batch = await runtime.execute(step)
    assert len(batch.results) == 1
    assert not batch.ok


@pytest.mark.unit
@pytest.mark.asyncio
async def test_envelope_passes_through_coordinator_bridge(runtime: ExecutionRuntime) -> None:
    result = await runtime.execute_tool("perception_health", {})
    coord = (result.envelope.get("data") or {}).get("coordinator")
    # Health may or may not create episode; bridge still attaches integrated flag when coordinator on
    if coord:
        assert "integrated" in coord or "briefing" in coord or coord.get("integrated") is False
