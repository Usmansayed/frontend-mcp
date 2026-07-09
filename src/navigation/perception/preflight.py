"""Preflight checks and condition-based waits (replaces fixed sleeps)."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .verification import evaluate_js, read_current_url


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    url: str = ""
    error: str | None = None
    degraded: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "url": self.url,
            "error": self.error,
            "degraded": list(self.degraded),
        }


async def wait_for_page_ready(
    session: Any,
    *,
    timeout: float = 15.0,
    poll: float = 0.1,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = await evaluate_js(session, "document.readyState")
        if state == "complete":
            return True
        await asyncio.sleep(poll)
    return False


async def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 10.0,
    poll: float = 0.15,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(poll)
    return False


async def wait_until_async(
    predicate: Callable[[], Any],
    *,
    timeout: float = 10.0,
    poll: float = 0.15,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(poll)
    return False


async def preflight_check(
    session: Any,
    url: str,
    *,
    ready_timeout: float = 15.0,
) -> PreflightResult:
    """Navigate to url and verify the page is reachable."""
    degraded: list[str] = []
    try:
        await session.navigate_to(url)
    except Exception as exc:
        return PreflightResult(ok=False, url=url, error=f"navigate failed: {exc}")

    current = await read_current_url(session)
    if not current:
        return PreflightResult(ok=False, url=url, error="empty url after navigation")

    if not await wait_for_page_ready(session, timeout=ready_timeout):
        degraded.append("ready_state_timeout")

    return PreflightResult(ok=True, url=current, degraded=degraded)
