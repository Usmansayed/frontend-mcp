"""Browser session lifecycle for MCP tools."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.design_workflow_intelligence.state.state_manager import StateManager
from navigation.frontend_quality_intelligence.console.service import SessionConsoleService
from navigation.frontend_quality_intelligence.network.service import SessionNetworkService
from navigation.visual_browser_intelligence.browser.browser_session_manager import (
    BrowserSessionManager,
    ManagedBrowser,
)

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    session_id: str
    base_url: str
    browser: Any
    artifacts_dir: Path
    state_manager: StateManager = field(default_factory=StateManager)
    console: SessionConsoleService = field(default_factory=SessionConsoleService)
    network: SessionNetworkService = field(default_factory=SessionNetworkService)
    run_counter: int = 0
    current_run_id: str = ""
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    _manager_lease_id: str = ""
    _manager_isolated: bool = False
    _manager_browser_id: str = ""

    def next_run_id(self) -> str:
        self.run_counter += 1
        self.current_run_id = f"run_{self.run_counter:04d}"
        return self.current_run_id

    def rebind(self, managed: ManagedBrowser) -> None:
        self.browser = managed.browser
        self.console = managed.console
        self.network = managed.network
        self._manager_lease_id = managed.lease_id
        self._manager_isolated = managed.isolated
        self._manager_browser_id = managed.browser_id
        self.headless = managed.headless
        self.viewport_width = managed.viewport_width
        self.viewport_height = managed.viewport_height


class SessionStore:
    def __init__(
        self,
        artifacts_root: Path | None = None,
        *,
        manager: BrowserSessionManager | None = None,
    ) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._artifacts_root = artifacts_root or Path.cwd() / "artifacts" / "mcp"
        self._manager = manager or BrowserSessionManager.get()

    @property
    def manager(self) -> BrowserSessionManager:
        return self._manager

    def get(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def require(self, session_id: str) -> SessionRecord:
        """Sync lookup — prefer ensure() from async tool handlers for recovery."""
        rec = self.get(session_id)
        if rec is None:
            raise KeyError(f"unknown session_id: {session_id}")
        self._manager.touch()
        return rec

    async def ensure(self, session_id: str) -> SessionRecord:
        """Require session and recover browser handle if user closed / crashed."""
        rec = self.require(session_id)
        managed = await self._manager.ensure_alive(
            base_url=rec.base_url,
            headless=rec.headless,
            viewport_width=rec.viewport_width,
            viewport_height=rec.viewport_height,
        )
        if managed is not None and (
            rec.browser is not managed.browser
            or rec._manager_browser_id != managed.browser_id
        ):
            logger.info(
                "rebinding session %s to recovered browser %s",
                session_id,
                managed.browser_id,
            )
            rec.rebind(managed)
        self._manager.touch()
        return rec

    async def start(
        self,
        *,
        base_url: str,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        isolated: bool = False,
    ) -> SessionRecord:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        artifacts_dir = self._artifacts_root / session_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        managed: ManagedBrowser = await self._manager.acquire(
            base_url=base_url.rstrip("/"),
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            isolated=isolated,
            logical_session_id=session_id,
        )
        self._manager.touch()

        rec = SessionRecord(
            session_id=session_id,
            base_url=base_url.rstrip("/"),
            browser=managed.browser,
            artifacts_dir=artifacts_dir,
            console=managed.console,
            network=managed.network,
            headless=managed.headless,
            viewport_width=managed.viewport_width,
            viewport_height=managed.viewport_height,
            _manager_lease_id=managed.lease_id,
            _manager_isolated=managed.isolated,
            _manager_browser_id=managed.browser_id,
        )
        rec.next_run_id()
        self._sessions[session_id] = rec
        self._manager.register_logical_session(session_id)
        return rec

    async def end(self, session_id: str) -> bool:
        rec = self._sessions.pop(session_id, None)
        if rec is None:
            return False
        await self._manager.release(
            isolated=rec._manager_isolated,
            lease_id=rec._manager_lease_id or None,
            logical_session_id=session_id,
        )
        return True

    async def end_all(self) -> None:
        for sid in list(self._sessions):
            await self.end(sid)
        await self._manager.end_all()

    async def reset_browser(self) -> None:
        """Explicit browser reset — kills shared Chromium, invalidates logical sessions."""
        self._sessions.clear()
        await self._manager.reset()
