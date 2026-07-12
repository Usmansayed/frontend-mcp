"""Execution Runtime — deterministic infrastructure beneath Coordination Intelligence."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import CompiledStep
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.execution_runtime.dispatch_registry import DispatchRegistry
from navigation.execution_runtime.executor import ToolExecutor
from navigation.execution_runtime.ledger import ExecutionLedger
from navigation.execution_runtime.models import CompiledExecutionResult, ExecutionResult
from navigation.execution_runtime.observability import ExecutionMetrics, ExecutionTrace
from navigation.execution_runtime.policies.config import ExecutionPolicies
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


class ExecutionRuntime:
    """Owns dispatch, execution, and ledger for a single MCP server instance."""

    def __init__(
        self,
        store: SessionStore,
        scans: ScanRegistry,
        snapshots: SnapshotRegistry,
        *,
        ledger: ExecutionLedger | None = None,
        policies: ExecutionPolicies | None = None,
    ) -> None:
        registry = DispatchRegistry.build(store, scans, snapshots)
        self._policies = policies or ExecutionPolicies()
        self._registry = registry
        self._executor = ToolExecutor(registry, ledger=ledger, policies=self._policies)

    @property
    def executor(self) -> ToolExecutor:
        return self._executor

    @property
    def registry(self) -> DispatchRegistry:
        return self._registry

    @property
    def ledger(self) -> ExecutionLedger:
        return self._executor.ledger

    @property
    def policies(self) -> ExecutionPolicies:
        return self._policies

    @property
    def trace(self) -> ExecutionTrace | None:
        return self._policies.trace

    @property
    def metrics(self) -> ExecutionMetrics | None:
        return self._policies.metrics

    async def execute_tool(
        self,
        tool: str,
        arguments: dict[str, Any] | None = None,
        *,
        allow_repeat: bool = False,
    ) -> ExecutionResult:
        return await self._executor.execute_tool(tool, arguments, allow_repeat=allow_repeat)

    async def execute(
        self,
        compiled_step: CompiledStep | dict[str, Any],
        *,
        allow_repeat: bool = False,
    ) -> CompiledExecutionResult:
        return await self._executor.execute(compiled_step, allow_repeat=allow_repeat)


_default_runtime: ExecutionRuntime | None = None


def configure(runtime: ExecutionRuntime) -> None:
    """Bind the module-level execute() to a server-scoped runtime."""
    global _default_runtime
    _default_runtime = runtime


def get_runtime() -> ExecutionRuntime | None:
    return _default_runtime


async def execute(
    compiled_step: CompiledStep | dict[str, Any],
    *,
    runtime: ExecutionRuntime | None = None,
    allow_repeat: bool = False,
) -> CompiledExecutionResult:
    """Public interface — execute a coordinator CompiledStep."""
    rt = runtime or _default_runtime
    if rt is None:
        raise RuntimeError(
            "ExecutionRuntime not configured. Pass runtime= or call configure() first."
        )
    return await rt.execute(compiled_step, allow_repeat=allow_repeat)
