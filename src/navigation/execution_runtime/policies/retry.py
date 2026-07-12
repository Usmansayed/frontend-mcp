"""Retry policies — deterministic retry decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from navigation.execution_runtime.policies.failures import FailureClass
from navigation.execution_runtime.policies.safe_tools import SafeToolRegistry


class RetryDecision(str, Enum):
    RETRY = "retry"
    ABORT = "abort"
    STOP = "stop"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts_safe: int = 3
    max_attempts_mutating: int = 1
    backoff_ms: int = 0

    def max_attempts_for(self, tool: str, safe_registry: SafeToolRegistry) -> int:
        if safe_registry.is_safe(tool):
            return self.max_attempts_safe
        return self.max_attempts_mutating


def evaluate_retry(
    *,
    tool: str,
    failure_class: FailureClass,
    attempt: int,
    policy: RetryPolicy,
    safe_registry: SafeToolRegistry,
    allow_repeat: bool = False,
) -> RetryDecision:
    if failure_class == FailureClass.NONE:
        return RetryDecision.STOP
    if failure_class == FailureClass.CANCELLED:
        return RetryDecision.ABORT
    if failure_class == FailureClass.PERMANENT:
        return RetryDecision.ABORT

    max_attempts = policy.max_attempts_for(tool, safe_registry)
    if not safe_registry.allows_retry(tool, allow_repeat=allow_repeat):
        max_attempts = 1

    if failure_class in (FailureClass.TRANSIENT, FailureClass.TIMEOUT, FailureClass.UNKNOWN):
        if attempt < max_attempts:
            return RetryDecision.RETRY
        return RetryDecision.ABORT

    return RetryDecision.ABORT
