"""Preflight checks and condition-based waits (replaces fixed sleeps)."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url


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


async def wait_for_spa_navigation_settle(
    session: Any,
    *,
    url_before: str,
    timeout: float = 6.0,
    poll: float = 0.12,
    stable_polls: int = 2,
) -> dict[str, Any]:
    """Wait for client-side route transitions where readyState stays ``complete``.

    Next.js App Router often updates ``location`` / ``document.title`` after the
    click while readyState never leaves complete — a plain ready wait races the
    observe snapshot (title/content mismatch).
    """
    deadline = time.monotonic() + timeout
    before = str(url_before or "").strip()
    last_url = ""
    last_title = ""
    stable = 0
    changed = False
    while time.monotonic() < deadline:
        meta = await evaluate_js(
            session,
            "({ url: location.href || '', title: document.title || '', ready: document.readyState || '' })",
        )
        if not isinstance(meta, dict):
            await asyncio.sleep(poll)
            continue
        url = str(meta.get("url") or "")
        title = str(meta.get("title") or "")
        if before and url and url != before:
            changed = True
        if url == last_url and title == last_title and url:
            stable += 1
            if changed and stable >= stable_polls:
                return {"ok": True, "url": url, "title": title, "changed": True}
            if not before and stable >= stable_polls:
                return {"ok": True, "url": url, "title": title, "changed": False}
        else:
            stable = 0
            last_url = url
            last_title = title
        await asyncio.sleep(poll)
    # Timed out — return last known meta; caller may still observe.
    return {
        "ok": changed and bool(last_url),
        "url": last_url,
        "title": last_title,
        "changed": changed,
        "timed_out": True,
    }


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
