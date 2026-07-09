"""Browser session lifecycle for MCP tools."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.perception.state_manager import StateManager
from navigation.console.service import SessionConsoleService
from navigation.network.service import SessionNetworkService


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

    def next_run_id(self) -> str:
        self.run_counter += 1
        self.current_run_id = f"run_{self.run_counter:04d}"
        return self.current_run_id


class SessionStore:
    def __init__(self, artifacts_root: Path | None = None) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._artifacts_root = artifacts_root or Path.cwd() / "artifacts" / "mcp"

    def get(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def require(self, session_id: str) -> SessionRecord:
        rec = self.get(session_id)
        if rec is None:
            raise KeyError(f"unknown session_id: {session_id}")
        return rec

    async def start(
        self,
        *,
        base_url: str,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
    ) -> SessionRecord:
        from browser_use import BrowserProfile, BrowserSession

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        artifacts_dir = self._artifacts_root / session_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        browser = BrowserSession(
            browser_profile=BrowserProfile(
                headless=headless,
                viewport={"width": viewport_width, "height": viewport_height},
            )
        )
        await browser.start()
        await browser.navigate_to(base_url.rstrip("/"))

        rec = SessionRecord(
            session_id=session_id,
            base_url=base_url.rstrip("/"),
            browser=browser,
            artifacts_dir=artifacts_dir,
        )
        await rec.console.attach(browser)
        await rec.network.attach(browser)
        rec.next_run_id()
        self._sessions[session_id] = rec
        return rec

    async def end(self, session_id: str) -> bool:
        rec = self._sessions.pop(session_id, None)
        if rec is None:
            return False
        try:
            rec.console.detach()
        except Exception:
            pass
        try:
            rec.network.detach()
        except Exception:
            pass
        try:
            await rec.browser.kill()
        except Exception:
            pass
        return True

    async def end_all(self) -> None:
        for sid in list(self._sessions):
            await self.end(sid)
