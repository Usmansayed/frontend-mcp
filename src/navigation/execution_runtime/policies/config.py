"""Bundled execution policies."""

from __future__ import annotations

from dataclasses import dataclass, field

from navigation.execution_runtime.idempotency import IdempotencyStore
from navigation.execution_runtime.observability import ExecutionMetrics, ExecutionTrace, new_correlation_id
from navigation.execution_runtime.policies.cancellation import CancellationToken
from navigation.execution_runtime.policies.retry import RetryPolicy
from navigation.execution_runtime.policies.safe_tools import SafeToolRegistry
from navigation.execution_runtime.policies.timeout import DEFAULT_TIMEOUT_POLICY, TimeoutPolicy


@dataclass
class FailureInjector:
    """Test-only hook: tool -> failure class per attempt (1-based)."""

    rules: dict[str, list[str]] = field(default_factory=dict)

    def failure_for(self, tool: str, attempt: int) -> str | None:
        seq = self.rules.get(tool) or []
        if attempt - 1 < len(seq):
            return seq[attempt - 1]
        return None


@dataclass
class ExecutionPolicies:
    timeout: TimeoutPolicy = field(default_factory=lambda: DEFAULT_TIMEOUT_POLICY)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    safe_tools: SafeToolRegistry = field(default_factory=SafeToolRegistry)
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    idempotency: IdempotencyStore = field(default_factory=IdempotencyStore)
    failure_injector: FailureInjector | None = None
    correlation_id: str | None = None
    trace: ExecutionTrace | None = None
    metrics: ExecutionMetrics | None = None

    def ensure_observability(self) -> tuple[str, ExecutionTrace, ExecutionMetrics]:
        corr = self.correlation_id or new_correlation_id()
        self.correlation_id = corr
        if self.trace is None:
            self.trace = ExecutionTrace(correlation_id=corr)
        if self.metrics is None:
            self.metrics = ExecutionMetrics()
        return corr, self.trace, self.metrics
