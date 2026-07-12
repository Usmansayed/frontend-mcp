"""Execution observability — correlation, traces, metrics."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger("navigation.execution_runtime")


def new_correlation_id() -> str:
    return f"corr_{uuid4().hex[:16]}"


@dataclass
class ExecutionTraceEvent:
    event: str
    tool: str | None = None
    execution_id: str | None = None
    correlation_id: str | None = None
    attempt: int | None = None
    latency_ms: int | None = None
    failure_class: str | None = None
    recovery_trigger: str | None = None
    replayed: bool = False
    cancelled: bool = False
    detail: str | None = None
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "tool": self.tool,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "attempt": self.attempt,
            "latency_ms": self.latency_ms,
            "failure_class": self.failure_class,
            "recovery_trigger": self.recovery_trigger,
            "replayed": self.replayed,
            "cancelled": self.cancelled,
            "detail": self.detail,
            "timestamp_ms": self.timestamp_ms,
        }


@dataclass
class ExecutionTrace:
    correlation_id: str
    events: list[ExecutionTraceEvent] = field(default_factory=list)

    def record(self, event: ExecutionTraceEvent) -> None:
        self.events.append(event)
        logger.info(
            "execution_event",
            extra={
                "execution_event": event.to_dict(),
                "correlation_id": self.correlation_id,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "events": [e.to_dict() for e in self.events],
        }


@dataclass
class ExecutionMetrics:
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    retried_calls: int = 0
    replayed_calls: int = 0
    cancelled_calls: int = 0
    total_latency_ms: int = 0

    def record(
        self,
        *,
        ok: bool,
        latency_ms: int,
        retried: bool = False,
        replayed: bool = False,
        cancelled: bool = False,
    ) -> None:
        self.total_calls += 1
        self.total_latency_ms += latency_ms
        if cancelled:
            self.cancelled_calls += 1
        elif replayed:
            self.replayed_calls += 1
        elif ok:
            self.success_calls += 1
        else:
            self.failed_calls += 1
        if retried:
            self.retried_calls += 1

    @property
    def mean_latency_ms(self) -> float:
        if self.total_calls <= 0:
            return 0.0
        return round(self.total_latency_ms / self.total_calls, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "failed_calls": self.failed_calls,
            "retried_calls": self.retried_calls,
            "replayed_calls": self.replayed_calls,
            "cancelled_calls": self.cancelled_calls,
            "total_latency_ms": self.total_latency_ms,
            "mean_latency_ms": self.mean_latency_ms,
            "success_rate": round(self.success_calls / max(self.total_calls, 1), 4),
        }
