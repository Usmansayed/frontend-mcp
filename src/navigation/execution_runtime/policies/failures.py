"""Failure classification — deterministic categories for retry/recovery."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any


class FailureClass(str, Enum):
    NONE = "none"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection refused",
    "connection reset",
    "temporarily unavailable",
    "econnreset",
    "econnrefused",
    "network",
    "503",
    "502",
    "504",
)

_PERMANENT_MARKERS = (
    "unknown tool",
    "requires_human",
    "auth_gate",
    "invalid",
    "not found",
    "forbidden",
    "unauthorized",
    "permanent failure",
    "400",
    "401",
    "403",
    "404",
)


def classify_failure(
    *,
    tool: str,
    envelope: dict[str, Any] | None = None,
    error: str | None = None,
    exc: BaseException | None = None,
) -> FailureClass:
    if isinstance(exc, asyncio.CancelledError):
        return FailureClass.CANCELLED
    if isinstance(exc, asyncio.TimeoutError):
        return FailureClass.TIMEOUT

    env = envelope or {}
    if env.get("ok") is not False and not error and not exc:
        return FailureClass.NONE

    msg = (error or env.get("error") or str(exc or "")).lower()
    data = env.get("data") or {}
    coord = data.get("coordinator") or {}
    briefing = coord.get("briefing") or {}
    stop = (briefing.get("stop_reason") or coord.get("stop_reason") or "").lower()

    if "cancel" in msg:
        return FailureClass.CANCELLED
    if "timeout" in msg or "timed out" in msg:
        return FailureClass.TIMEOUT
    if "unknown tool" in msg:
        return FailureClass.PERMANENT
    if "requires_human" in stop or "auth" in stop:
        return FailureClass.PERMANENT
    if any(m in msg for m in _PERMANENT_MARKERS):
        return FailureClass.PERMANENT

    degraded = [str(d).lower() for d in (env.get("degraded") or [])]
    if any("unavailable" in d or "failed" in d for d in degraded):
        return FailureClass.TRANSIENT

    summary = (data.get("agent_summary") or {})
    if summary.get("blocking"):
        return FailureClass.PERMANENT

    if any(m in msg for m in _TRANSIENT_MARKERS):
        return FailureClass.TRANSIENT

    if env.get("ok") is False:
        return FailureClass.UNKNOWN
    return FailureClass.NONE
