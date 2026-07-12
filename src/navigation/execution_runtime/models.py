"""Execution Runtime models — deterministic infrastructure only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_execution_id() -> str:
    return f"ex_{uuid4().hex[:16]}"


def _new_correlation_id() -> str:
    return f"corr_{uuid4().hex[:16]}"


@dataclass
class ExecutionMetadata:
    execution_id: str
    correlation_id: str
    tool: str
    attempt: int
    latency_ms: int
    failure_class: str = "none"
    recovery_trigger: str | None = None
    replayed: bool = False
    cancelled: bool = False
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "tool": self.tool,
            "attempt": self.attempt,
            "latency_ms": self.latency_ms,
            "failure_class": self.failure_class,
            "recovery_trigger": self.recovery_trigger,
            "replayed": self.replayed,
            "cancelled": self.cancelled,
            "idempotency_key": self.idempotency_key,
        }


def attach_execution_metadata(envelope: dict[str, Any], metadata: ExecutionMetadata) -> dict[str, Any]:
    data = envelope.setdefault("data", {})
    data["execution"] = metadata.to_dict()
    return envelope


@dataclass
class ExecutionRecord:
    execution_id: str
    tool: str
    ok: bool
    latency_ms: int
    correlation_id: str | None = None
    error: str | None = None
    session_id: str | None = None
    episode_id: str | None = None
    attempt: int = 1
    failure_class: str = "none"
    recovery_trigger: str | None = None
    replayed: bool = False
    cancelled: bool = False
    idempotency_key: str | None = None
    timestamp: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool": self.tool,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "correlation_id": self.correlation_id,
            "error": self.error,
            "session_id": self.session_id,
            "episode_id": self.episode_id,
            "attempt": self.attempt,
            "failure_class": self.failure_class,
            "recovery_trigger": self.recovery_trigger,
            "replayed": self.replayed,
            "cancelled": self.cancelled,
            "idempotency_key": self.idempotency_key,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionResult:
    """Result of a single tool invocation through the execution runtime."""

    execution_id: str
    tool: str
    envelope: dict[str, Any]
    latency_ms: int
    attempt: int = 1
    correlation_id: str | None = None
    failure_class: str = "none"
    recovery_trigger: str | None = None
    replayed: bool = False
    cancelled: bool = False
    record: ExecutionRecord | None = None

    @property
    def ok(self) -> bool:
        return bool(self.envelope.get("ok")) and not self.cancelled

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool": self.tool,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "attempt": self.attempt,
            "correlation_id": self.correlation_id,
            "failure_class": self.failure_class,
            "recovery_trigger": self.recovery_trigger,
            "replayed": self.replayed,
            "cancelled": self.cancelled,
            "envelope": self.envelope,
            "record": self.record.to_dict() if self.record else None,
        }


@dataclass
class CompiledExecutionResult:
    """Result of executing a coordinator CompiledStep."""

    capability_id: str | None
    semantic_action: str | None
    step_id: str | None
    playbook_id: str | None
    results: list[ExecutionResult]
    ok: bool
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "semantic_action": self.semantic_action,
            "step_id": self.step_id,
            "playbook_id": self.playbook_id,
            "ok": self.ok,
            "correlation_id": self.correlation_id,
            "results": [r.to_dict() for r in self.results],
        }
