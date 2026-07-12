"""Recovery policies — map failures to replan triggers (advisory hooks)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from navigation.execution_runtime.policies.failures import FailureClass


class RecoveryAction(str, Enum):
    NONE = "none"
    RETRY_VERIFY = "TR_VERIFY_FAIL"
    STOP_AUTH = "TR_AUTH_REQUIRED"
    DEGRADED_FALLBACK = "TR_DEGRADED_UPSTREAM"
    STOP_INVARIANT = "TR_INVARIANT_VIOLATION"
    SESSION_RESTART = "TR_SESSION_LOST"
    ENV_DOWN = "TR_DEV_SERVER_DOWN"
    STOP_EXHAUSTED = "TR_VERIFY_EXHAUSTED"
    ABORT = "abort"


@dataclass(frozen=True)
class RecoveryHint:
    action: RecoveryAction
    trigger_id: str
    detail: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "action": self.action.value,
            "trigger_id": self.trigger_id,
            "detail": self.detail,
        }


def evaluate_recovery(
    *,
    tool: str,
    envelope: dict[str, Any],
    failure_class: FailureClass,
) -> RecoveryHint:
    if envelope.get("ok") is not False and failure_class == FailureClass.NONE:
        return RecoveryHint(RecoveryAction.NONE, "none")

    data = envelope.get("data") or {}
    coord = data.get("coordinator") or {}
    briefing = coord.get("briefing") or {}
    stop = briefing.get("stop_reason") or coord.get("stop_reason")

    if stop and "TR_AUTH" in str(stop):
        return RecoveryHint(RecoveryAction.STOP_AUTH, "TR_AUTH_REQUIRED", str(stop))
    if stop and "TR_VERIFY_EXHAUSTED" in str(stop):
        return RecoveryHint(RecoveryAction.STOP_EXHAUSTED, "TR_VERIFY_EXHAUSTED", str(stop))
    if stop and str(stop).startswith("TR_"):
        return RecoveryHint(RecoveryAction.STOP_INVARIANT, str(stop), str(stop))

    auth = data.get("auth_gate") or {}
    if auth.get("requires_human"):
        return RecoveryHint(RecoveryAction.STOP_AUTH, "TR_AUTH_REQUIRED", "auth_gate_requires_human")

    degraded = [str(d).lower() for d in (envelope.get("degraded") or [])]
    if any("unavailable" in d for d in degraded):
        return RecoveryHint(RecoveryAction.DEGRADED_FALLBACK, "TR_DEGRADED_UPSTREAM")

    if tool == "perception_verify" and failure_class != FailureClass.NONE:
        return RecoveryHint(RecoveryAction.RETRY_VERIFY, "TR_VERIFY_FAIL", "verify_failed")

    if tool == "perception_health" and failure_class in (
        FailureClass.TRANSIENT,
        FailureClass.TIMEOUT,
        FailureClass.UNKNOWN,
    ):
        return RecoveryHint(RecoveryAction.ENV_DOWN, "TR_DEV_SERVER_DOWN")

    if failure_class == FailureClass.CANCELLED:
        return RecoveryHint(RecoveryAction.ABORT, "cancelled")

    if failure_class == FailureClass.PERMANENT:
        return RecoveryHint(RecoveryAction.ABORT, "permanent_failure", envelope.get("error"))

    if failure_class == FailureClass.TIMEOUT:
        return RecoveryHint(RecoveryAction.RETRY_VERIFY, "TR_VERIFY_FAIL", "execution_timeout")

    return RecoveryHint(RecoveryAction.NONE, "none")
