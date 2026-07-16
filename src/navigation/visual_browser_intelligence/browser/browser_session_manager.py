"""Browser Session Manager — single source of truth for Chromium lifecycle.

Professional-desktop rules:
  - One primary browser per MCP process.
  - Tools acquire/reuse; they never launch or kill browsers themselves.
  - User may close the window anytime; next acquire recovers transparently.
  - No profile-mismatch auto-isolation (that spawned extra headed windows).
  - Isolated browsers only with PERCEPTION_ALLOW_ISOLATED_BROWSER=1 (exceptional).
"""
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


def same_origin(a: str, b: str) -> bool:
    """True when both URLs share scheme+host(+port). Empty either side → False."""
    from urllib.parse import urlparse

    if not a or not b:
        return False
    pa, pb = urlparse(a), urlparse(b)
    if not pa.scheme or not pa.netloc or not pb.scheme or not pb.netloc:
        return False
    return (pa.scheme, pa.netloc.lower()) == (pb.scheme, pb.netloc.lower())


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
    browser_id: str = field(default_factory=lambda: f"br_{uuid.uuid4().hex[:12]}")
    launched_at: float = field(default_factory=time.monotonic)
    last_activity_at: float = field(default_factory=time.monotonic)
    isolated: bool = False
    # App session URL parked before guest tools (inspiration/figma) navigate away.
    parked_url: str = ""
    app_base_url: str = ""


class BrowserSessionManager:
    """Owns Chromium launch, reuse, recovery, idle shutdown, and process exit."""

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
        # Exceptional only (env-gated) — not used in normal MCP operation
        self._isolated_browsers: dict[str, ManagedBrowser] = {}
        self._isolated_refs: dict[str, int] = {}
        self._logical_sessions: set[str] = set()
        self._restart_count = 0
        self._last_close_reason: str | None = None
        self._last_disconnect_at: float | None = None
        self._allow_isolated = os.environ.get(
            "PERCEPTION_ALLOW_ISOLATED_BROWSER", ""
        ).strip().lower() in ("1", "true", "yes")

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

    @property
    def restart_count(self) -> int:
        return self._restart_count

    def register_logical_session(self, session_id: str) -> None:
        if session_id:
            self._logical_sessions.add(session_id)

    def unregister_logical_session(self, session_id: str) -> None:
        self._logical_sessions.discard(session_id)

    def diagnostics(self) -> dict[str, Any]:
        """Snapshot for perception_health — no side effects."""
        managed = self._managed
        idle_seconds: float | None = None
        browser_running = False
        browser_connected = False
        browser_id = None
        owned_pages = 0
        headless = None
        if managed is not None:
            browser_id = managed.browser_id
            headless = managed.headless
            idle_seconds = round(time.monotonic() - managed.last_activity_at, 1)
            browser = managed.browser
            try:
                if hasattr(browser, "is_cdp_connected"):
                    connected = browser.is_cdp_connected
                    browser_connected = bool(
                        connected() if callable(connected) else connected
                    )
                else:
                    browser_connected = True
            except Exception:
                browser_connected = False
            browser_running = browser_connected
            try:
                if hasattr(browser, "get_pages"):
                    pages = browser.get_pages
                    result = pages() if callable(pages) else pages
                    if asyncio.iscoroutine(result):
                        owned_pages = -1  # async; use tabs sync path below
                    elif result is not None:
                        owned_pages = len(list(result))
                if owned_pages <= 0 and hasattr(browser, "get_tabs"):
                    tabs = browser.get_tabs
                    result = tabs() if callable(tabs) else tabs
                    if not asyncio.iscoroutine(result) and result is not None:
                        owned_pages = len(list(result))
            except Exception:
                owned_pages = 0

        return {
            "browser_running": browser_running and managed is not None,
            "browser_connected": browser_connected and managed is not None,
            "browser_id": browser_id,
            "headless": headless,
            "active_sessions": len(self._logical_sessions),
            "active_leases": self._ref_count,
            "active_tools": self._ref_count,
            "idle_seconds": idle_seconds if managed is not None else None,
            "owned_pages": max(0, owned_pages) if managed is not None else 0,
            "restart_count": self._restart_count,
            "isolated_browsers": len(self._isolated_browsers),
            "last_close_reason": self._last_close_reason,
            "idle_timeout_s": self._idle_timeout_s,
            "allow_isolated": self._allow_isolated,
        }

    async def acquire(
        self,
        *,
        base_url: str = "",
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        isolated: bool = False,
        logical_session_id: str | None = None,
    ) -> ManagedBrowser:
        """Acquire the primary browser (launch or reuse). Never auto-spawns duplicates."""
        async with self._lock:
            self._cancel_idle_timer()
            normalized_url = (base_url or "").rstrip("/")

            if isolated:
                if self._allow_isolated:
                    logger.warning(
                        "isolated browser requested (exceptional) — lease will be tracked separately"
                    )
                    managed = await self._acquire_isolated(
                        base_url=normalized_url,
                        headless=headless,
                        viewport_width=viewport_width,
                        viewport_height=viewport_height,
                    )
                    if logical_session_id:
                        self._logical_sessions.add(logical_session_id)
                    return managed
                logger.warning(
                    "isolated=True ignored — single browser policy "
                    "(set PERCEPTION_ALLOW_ISOLATED_BROWSER=1 to override)"
                )

            await self._reconcile_dead_primary(reason_hint="acquire")

            if self._managed is not None and await self._is_alive(self._managed):
                # Soft profile: keep existing Chromium; never spawn a second window.
                if self._profile_differs(self._managed, headless, viewport_width, viewport_height):
                    logger.info(
                        "profile request differs (asked headless=%s %sx%s, have headless=%s %sx%s) "
                        "— reusing primary browser",
                        headless,
                        viewport_width,
                        viewport_height,
                        self._managed.headless,
                        self._managed.viewport_width,
                        self._managed.viewport_height,
                    )
                self._ref_count += 1
                self._touch()
                await self._ensure_base_url(self._managed, normalized_url)
                if logical_session_id:
                    self._logical_sessions.add(logical_session_id)
                return self._managed

            recovering = self._ref_count > 0 or bool(self._logical_sessions) or (
                self._last_close_reason in ("acquire", "ensure_alive", "user_closed", "crashed")
            )
            managed = await self._launch(
                base_url=normalized_url,
                headless=headless,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
            )
            self._managed = managed
            # Preserve existing leases that survived a dead-browser clear, then add this acquire.
            self._ref_count = max(self._ref_count, 0) + 1
            if recovering and self._last_close_reason:
                self._restart_count += 1
            if logical_session_id:
                self._logical_sessions.add(logical_session_id)
            return managed

    async def release(
        self,
        *,
        isolated: bool = False,
        lease_id: str | None = None,
        logical_session_id: str | None = None,
    ) -> None:
        async with self._lock:
            if logical_session_id:
                self._logical_sessions.discard(logical_session_id)

            if isolated and lease_id:
                refs = self._isolated_refs.get(lease_id, 0) - 1
                if refs <= 0:
                    managed = self._isolated_browsers.pop(lease_id, None)
                    self._isolated_refs.pop(lease_id, None)
                    if managed:
                        await self._kill_one(managed, reason="isolated_release")
                else:
                    self._isolated_refs[lease_id] = refs
                return

            # If caller thought this was isolated but it was soft-shared, release shared.
            if lease_id and lease_id in self._isolated_browsers:
                refs = self._isolated_refs.get(lease_id, 0) - 1
                if refs <= 0:
                    managed = self._isolated_browsers.pop(lease_id, None)
                    self._isolated_refs.pop(lease_id, None)
                    if managed:
                        await self._kill_one(managed, reason="isolated_release")
                else:
                    self._isolated_refs[lease_id] = refs
                return

            self._ref_count = max(0, self._ref_count - 1)
            if self._ref_count == 0:
                self._schedule_idle_shutdown()

    async def note_user_closed(self) -> None:
        """Mark primary browser gone after detecting user close / disconnect."""
        async with self._lock:
            await self._clear_dead_primary(reason="user_closed")

    async def reset(self) -> None:
        """Explicit user/agent reset — kill browser immediately."""
        async with self._lock:
            self._cancel_idle_timer()
            await self._kill_managed(reason="reset")
            await self._kill_all_isolated(reason="reset")

    async def end_all(self) -> None:
        """Process shutdown / session_end_all — kill all browsers immediately."""
        async with self._lock:
            self._cancel_idle_timer()
            await self._kill_managed(reason="process_shutdown")
            await self._kill_all_isolated(reason="process_shutdown")
            self._logical_sessions.clear()

    def touch(self) -> None:
        if self._managed is not None:
            self._touch_managed(self._managed)

    async def park_current_url(self, *, app_base_url: str = "") -> str:
        """Snapshot live URL before a guest tool navigates to an external site."""
        managed = self._managed
        if managed is None or not await self._is_alive(managed):
            return ""
        if managed.parked_url:
            # Nested guest tools — keep outermost park.
            if app_base_url and not managed.app_base_url:
                managed.app_base_url = app_base_url.rstrip("/")
            return managed.parked_url
        try:
            from navigation.visual_browser_intelligence.verify.verification import (
                read_current_url,
            )

            live = (await read_current_url(managed.browser) or "").strip()
        except Exception:
            live = ""
        if not live:
            live = (managed.base_url or app_base_url or "").rstrip("/")
        managed.parked_url = live
        if app_base_url:
            managed.app_base_url = app_base_url.rstrip("/")
        elif not managed.app_base_url and managed.base_url:
            managed.app_base_url = managed.base_url.rstrip("/")
        logger.info("parked app url=%s before guest navigation", managed.parked_url)
        return managed.parked_url

    async def restore_parked_url(self) -> dict[str, Any]:
        """Navigate back to parked app URL; clear park. Verifies live URL origin."""
        managed = self._managed
        result: dict[str, Any] = {
            "attempted": False,
            "restored": False,
            "parked_url": "",
            "live_url": "",
        }
        if managed is None or not await self._is_alive(managed):
            return result
        target = (managed.parked_url or managed.app_base_url or managed.base_url or "").rstrip(
            "/"
        )
        if not target:
            return result
        result["attempted"] = True
        result["parked_url"] = target
        try:
            await managed.browser.navigate_to(target)
            from navigation.visual_browser_intelligence.verify.verification import (
                read_current_url,
            )

            live = (await read_current_url(managed.browser) or "").strip()
            result["live_url"] = live
            origin_ok = same_origin(live, target) or (
                bool(managed.app_base_url) and same_origin(live, managed.app_base_url)
            )
            # Also accept exact path match after normalize
            restored = origin_ok or live.rstrip("/") == target
            result["restored"] = restored
            if restored:
                managed.base_url = managed.app_base_url or target
            else:
                logger.warning(
                    "restore_parked_url origin mismatch parked=%s live=%s",
                    target,
                    live,
                )
        except Exception as exc:
            logger.warning("restore_parked_url failed: %s", exc)
            result["error"] = str(exc)
        finally:
            managed.parked_url = ""
        return result

    async def ensure_on_app_origin(
        self,
        *,
        app_base_url: str,
        preferred_url: str = "",
    ) -> dict[str, Any]:
        """If live URL is off the app origin, navigate back. Used by SessionStore.ensure."""
        managed = self._managed
        out: dict[str, Any] = {
            "checked": False,
            "restored": False,
            "live_url": "",
            "target_url": "",
        }
        if managed is None or not app_base_url:
            return out
        if not await self._is_alive(managed):
            return out
        out["checked"] = True
        try:
            from navigation.visual_browser_intelligence.verify.verification import (
                read_current_url,
            )

            live = (await read_current_url(managed.browser) or "").strip()
        except Exception:
            live = ""
        out["live_url"] = live
        if live and same_origin(live, app_base_url):
            return out
        target = (preferred_url or managed.parked_url or app_base_url).rstrip("/")
        out["target_url"] = target
        try:
            await managed.browser.navigate_to(target)
            live2 = ""
            try:
                from navigation.visual_browser_intelligence.verify.verification import (
                    read_current_url,
                )

                live2 = (await read_current_url(managed.browser) or "").strip()
            except Exception:
                pass
            out["live_url"] = live2 or live
            out["restored"] = same_origin(out["live_url"], app_base_url) or (
                out["live_url"].rstrip("/") == target
            )
            if out["restored"]:
                managed.base_url = app_base_url.rstrip("/")
                managed.parked_url = ""
        except Exception as exc:
            out["error"] = str(exc)
            logger.warning("ensure_on_app_origin failed: %s", exc)
        return out

    async def ensure_alive(
        self,
        *,
        base_url: str = "",
        headless: bool | None = None,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
    ) -> ManagedBrowser | None:
        """Recover primary browser if dead without bumping lease count (rebinding)."""
        async with self._lock:
            self._cancel_idle_timer()
            await self._reconcile_dead_primary(reason_hint="ensure_alive")
            if self._managed is not None and await self._is_alive(self._managed):
                self._touch()
                return self._managed
            if self._ref_count <= 0 and not self._logical_sessions:
                return None
            # Logical sessions still expect a browser — recover transparently.
            hl = headless if headless is not None else True
            vw = viewport_width if viewport_width is not None else 1920
            vh = viewport_height if viewport_height is not None else 1080
            if self._managed is not None:
                hl = self._managed.headless
                vw = self._managed.viewport_width
                vh = self._managed.viewport_height
                base = base_url or self._managed.base_url
            else:
                base = base_url
            self._restart_count += 1
            managed = await self._launch(
                base_url=(base or "").rstrip("/"),
                headless=hl,
                viewport_width=vw,
                viewport_height=vh,
            )
            self._managed = managed
            logger.info(
                "browser recovered (restart_count=%s reason=%s)",
                self._restart_count,
                self._last_close_reason or "unknown",
            )
            return managed

    async def _reconcile_dead_primary(self, *, reason_hint: str) -> None:
        if self._managed is None:
            return
        if await self._is_alive(self._managed):
            return
        await self._clear_dead_primary(reason=reason_hint)

    async def _clear_dead_primary(self, *, reason: str) -> None:
        managed = self._managed
        self._managed = None
        self._last_close_reason = reason
        self._last_disconnect_at = time.monotonic()
        if managed is not None:
            logger.info("primary browser gone (%s) — clearing handle without fighting close", reason)
            try:
                managed.console.detach()
            except Exception:
                pass
            try:
                managed.network.detach()
            except Exception:
                pass
            # Do not call kill() if already dead — user ownership.
            try:
                if await self._is_alive(managed):
                    await managed.browser.kill()
            except Exception:
                pass

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
        managed.isolated = True
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
        logger.info(
            "browser launched id=%s headless=%s viewport=%sx%s base_url=%s",
            managed.browser_id,
            headless,
            viewport_width,
            viewport_height,
            base_url,
        )
        return managed

    async def _ensure_base_url(self, managed: ManagedBrowser, base_url: str) -> None:
        if not base_url:
            return
        # Same origin already — do not bounce SPA to root.
        try:
            from navigation.visual_browser_intelligence.verify.verification import (
                read_current_url,
            )

            live = (await read_current_url(managed.browser) or "").strip()
        except Exception:
            live = ""
        if live and same_origin(live, base_url):
            if not managed.app_base_url:
                managed.app_base_url = base_url.rstrip("/")
            return
        if managed.base_url == base_url and live and same_origin(live, base_url):
            return
        try:
            await managed.browser.navigate_to(base_url)
            managed.base_url = base_url
            # Only update app_base_url for same-origin navigations (not gallery guests).
            if not managed.parked_url and (
                not managed.app_base_url or same_origin(base_url, managed.app_base_url)
            ):
                managed.app_base_url = base_url.rstrip("/")
        except Exception as exc:
            logger.warning("navigate to %s failed during reuse: %s", base_url, exc)

    @staticmethod
    def _profile_differs(
        managed: ManagedBrowser,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
    ) -> bool:
        return (
            managed.headless != headless
            or managed.viewport_width != viewport_width
            or managed.viewport_height != viewport_height
        )

    async def _is_alive(self, managed_or_browser: Any) -> bool:
        browser = (
            managed_or_browser.browser
            if isinstance(managed_or_browser, ManagedBrowser)
            else managed_or_browser
        )
        if browser is None:
            return False
        try:
            if hasattr(browser, "is_cdp_connected"):
                connected = browser.is_cdp_connected
                ok = connected() if callable(connected) else connected
                if ok is False:
                    return False
            if hasattr(browser, "is_running"):
                running = browser.is_running
                if callable(running):
                    result = running()
                    if asyncio.iscoroutine(result):
                        return bool(await result)
                    return bool(result)
                return bool(running)
            # Probe CDP session — fails if user closed the window.
            if hasattr(browser, "get_or_create_cdp_session"):
                await asyncio.wait_for(
                    browser.get_or_create_cdp_session(target_id=None, focus=False),
                    timeout=2.0,
                )
            return True
        except Exception:
            return False

    async def _kill_managed(self, *, reason: str) -> None:
        if self._managed is None:
            return
        await self._kill_one(self._managed, reason=reason)
        self._managed = None
        self._ref_count = 0
        self._last_close_reason = reason

    async def _kill_all_isolated(self, *, reason: str) -> None:
        for lease_id in list(self._isolated_browsers):
            managed = self._isolated_browsers.pop(lease_id, None)
            self._isolated_refs.pop(lease_id, None)
            if managed:
                await self._kill_one(managed, reason=reason)

    async def _kill_one(self, managed: ManagedBrowser, *, reason: str = "kill") -> None:
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
        self._last_close_reason = reason
        logger.debug("browser killed id=%s reason=%s", managed.browser_id, reason)

    def _touch(self) -> None:
        if self._managed is not None:
            self._touch_managed(self._managed)

    @staticmethod
    def _touch_managed(managed: ManagedBrowser) -> None:
        now = time.monotonic()
        managed.last_activity_at = now
        try:
            managed.browser._perception_last_activity = now  # type: ignore[attr-defined]
        except Exception:
            pass

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
                        await self._kill_managed(reason="idle_timeout")
            except asyncio.CancelledError:
                pass

        self._idle_task = asyncio.create_task(_idle_shutdown())
