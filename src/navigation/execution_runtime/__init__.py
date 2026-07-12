"""Execution Runtime — deterministic tool execution beneath Coordination Intelligence.

Public API:
    execute(compiled_step) — run a coordinator CompiledStep through MCP handlers.

No reasoning, routing, or playbook selection occurs in this package.
"""

from navigation.execution_runtime.runtime import (
    ExecutionRuntime,
    configure,
    execute,
    get_runtime,
)
from navigation.execution_runtime.models import (
    CompiledExecutionResult,
    ExecutionRecord,
    ExecutionResult,
)
from navigation.execution_runtime.policies import (
    CancellationToken,
    ExecutionPolicies,
    FailureClass,
    RetryDecision,
    SafeToolRegistry,
    TimeoutPolicy,
    classify_failure,
    evaluate_recovery,
    evaluate_retry,
)
from navigation.execution_runtime.observability import (
    ExecutionMetrics,
    ExecutionTrace,
    new_correlation_id,
)

__all__ = [
    "CancellationToken",
    "CompiledExecutionResult",
    "ExecutionMetrics",
    "ExecutionPolicies",
    "ExecutionRecord",
    "ExecutionResult",
    "ExecutionRuntime",
    "ExecutionTrace",
    "FailureClass",
    "RetryDecision",
    "SafeToolRegistry",
    "TimeoutPolicy",
    "classify_failure",
    "configure",
    "evaluate_recovery",
    "evaluate_retry",
    "execute",
    "get_runtime",
    "new_correlation_id",
]
