"""Shared browser episode lifecycle — one Chromium per MCP process when possible."""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from navigation.frontend_quality_intelligence.console.service import SessionConsoleService
from navigation.frontend_quality_intelligence.network.service import SessionNetworkService

logger = logging.getLogger(__name__)

_DEFAULT_IDLE_TIMEOUT_S = 600.0  # 10 minutes


@dataclass
class ManagedBrowser:
    """Physical browser episode shared across logical MCP sessions."""

    browser: Any
    headless: bool
    viewport_width: int
    viewport_height: int
    base_url: str
    console: SessionConsoleService = field(default_factory=SessionConsoleService)
    network: SessionNetworkService = field(default_factory=SessionNetworkService)
    lease_id: str = field(default_factory=lambda: f"lease_{uuid.uuid4().hex[:12]}")


class BrowserSessionManager:
    """Owns Chromium launch, reuse, idle shutdown, and explicit reset."""

    _default: BrowserSessionManager | None = None

    def __init__(self, *, idle_timeout_s: float | None = None) -> None:
        self._managed: ManagedBrowser | None = None
        self._ref_count = 0
        self._lock = asyncio.Lock()
        self._idle_timeout_s = float(
            idle_timeout_s
            if idle_timeout_s is not None
            else os.environ.get("PERCEPTION_BROWSER_IDLE_TIMEOUT_S", _DEFAULT_IDLE_TIMEOUT_S)
        )
        self._idle_task: asyncio.Task[None] | None = None
        self._isolated_browsers: dict[str, ManagedBrowser] = {}
        self._isolated_refs: dict[str, int] = {}

    @classmethod
    def get(cls) -> BrowserSessionManager:
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @classmethod
    def reset_default(cls) -> None:
        cls._default = None

    @property
    def has_active_browser(self) -> bool:
        return self._managed is not None and self._ref_count > 0

    @property
    def ref_count(self) -> int:
        return self._ref_count

    async def acquire(
        self,
        *,
        base_url: str,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        isolated: bool = False,
    ) -> ManagedBrowser:
        """Return a shared browser, launching only when none is alive."""
        async with self._lock:
            self._cancel_idle_timer()
            normalized_url = base_url.rstrip("/")

            if isolated:
                return await self._acquire_isolated(
                    base_url=normalized_url,
                    headless=headless,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                )

            if self._managed is not None and await self._is_alive(self._managed.browser):
                if self._profile_incompatible(self._managed, headless, viewport_width, viewport_height):
                    if self._ref_count > 0:
                        logger.debug(
                            "profile mismatch with active refs — isolated browser "
                            "(headless=%s viewport=%sx%s)",
                            headless,
                            viewport_width,
                            viewport_height,
                        )
                        return await self._acquire_isolated(
                            base_url=normalized_url,
                            headless=headless,
                            viewport_width=viewport_width,
                            viewport_height=viewport_height,
                        )
                    await self._kill_managed()
                else:
                    self._ref_count += 1
                    self._touch()
                    await self._ensure_base_url(self._managed, normalized_url)
                    return self._managed

            managed = await self._launch(
                base_url=normalized_url,
                headless=headless,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
            )
            self._managed = managed
            self._ref_count = 1
            return managed

    async def release(self, *, isolated: bool = False, lease_id: str | None = None) -> None:
        async with self._lock:
            if isolated and lease_id:
                refs = self._isolated_refs.get(lease_id, 0) - 1
                if refs <= 0:
                    managed = self._isolated_browsers.pop(lease_id, None)
                    self._isolated_refs.pop(lease_id, None)
                    if managed:
                        await self._kill_one(managed)
                else:
                    self._isolated_refs[lease_id] = refs
                return

            self._ref_count = max(0, self._ref_count - 1)
            if self._ref_count == 0:
                self._schedule_idle_shutdown()

    async def reset(self) -> None:
        """Explicit user/agent reset — kill browser immediately."""
        async with self._lock:
            self._cancel_idle_timer()
            await self._kill_managed()
            for lease_id in list(self._isolated_browsers):
                managed = self._isolated_browsers.pop(lease_id, None)
                self._isolated_refs.pop(lease_id, None)
                if managed:
                    await self._kill_one(managed)

    async def end_all(self) -> None:
        """Process shutdown — kill all browsers immediately."""
        async with self._lock:
            self._cancel_idle_timer()
            await self._kill_managed()
            for lease_id in list(self._isolated_browsers):
                managed = self._isolated_browsers.pop(lease_id, None)
                self._isolated_refs.pop(lease_id, None)
                if managed:
                    await self._kill_one(managed)

    def touch(self) -> None:
        if self._managed is not None:
            self._managed.browser._perception_last_activity = time.monotonic()  # type: ignore[attr-defined]

    async def _acquire_isolated(
        self,
        *,
        base_url: str,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
    ) -> ManagedBrowser:
        managed = await self._launch(
            base_url=base_url,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )
        self._isolated_browsers[managed.lease_id] = managed
        self._isolated_refs[managed.lease_id] = 1
        return managed

    async def _launch(
        self,
        *,
        base_url: str,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
    ) -> ManagedBrowser:
        from browser_use import BrowserProfile, BrowserSession

        browser = BrowserSession(
            browser_profile=BrowserProfile(
                headless=headless,
                viewport={"width": viewport_width, "height": viewport_height},
            )
        )
        await browser.start()
        if base_url:
            await browser.navigate_to(base_url)

        console = SessionConsoleService()
        network = SessionNetworkService()
        await console.attach(browser)
        await network.attach(browser)

        managed = ManagedBrowser(
            browser=browser,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            base_url=base_url,
            console=console,
            network=network,
        )
        self._touch_managed(managed)
        logger.debug(
            "browser launched headless=%s viewport=%sx%s base_url=%s",
            headless,
            viewport_width,
            viewport_height,
            base_url,
        )
        return managed

    async def _ensure_base_url(self, managed: ManagedBrowser, base_url: str) -> None:
        if not base_url or managed.base_url == base_url:
            return
        try:
            await managed.browser.navigate_to(base_url)
            managed.base_url = base_url
        except Exception as exc:
            logger.warning("navigate to %s failed during reuse: %s", base_url, exc)

    def _profile_incompatible(
        self,
        managed: ManagedBrowser,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
    ) -> bool:
        if managed.headless != headless:
            return True
        if managed.viewport_width != viewport_width or managed.viewport_height != viewport_height:
            return True
        return False

    async def _is_alive(self, browser: Any) -> bool:
        try:
            if hasattr(browser, "is_running"):
                return bool(await browser.is_running())  # type: ignore[misc]
            return browser is not None
        except Exception:
            return False

    async def _kill_managed(self) -> None:
        if self._managed is None:
            return
        await self._kill_one(self._managed)
        self._managed = None
        self._ref_count = 0

    async def _kill_one(self, managed: ManagedBrowser) -> None:
        try:
            managed.console.detach()
        except Exception:
            pass
        try:
            managed.network.detach()
        except Exception:
            pass
        try:
            await managed.browser.kill()
        except Exception:
            pass

    def _touch(self) -> None:
        if self._managed is not None:
            self._touch_managed(self._managed)

    @staticmethod
    def _touch_managed(managed: ManagedBrowser) -> None:
        managed.browser._perception_last_activity = time.monotonic()  # type: ignore[attr-defined]

    def _cancel_idle_timer(self) -> None:
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
        self._idle_task = None

    def _schedule_idle_shutdown(self) -> None:
        self._cancel_idle_timer()
        timeout = self._idle_timeout_s
        if timeout <= 0:
            return

        async def _idle_shutdown() -> None:
            try:
                await asyncio.sleep(timeout)
                async with self._lock:
                    if self._ref_count == 0 and self._managed is not None:
                        logger.info("browser idle timeout (%.0fs) — closing", timeout)
                        await self._kill_managed()
            except asyncio.CancelledError:
                pass

        self._idle_task = asyncio.create_task(_idle_shutdown())
