"""Phase 2: snapshot and restore browser state for stateful SPAs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url


@dataclass(slots=True)
class BrowserStateSnapshot:
    state_id: str
    url: str
    cookies: list[dict[str, Any]] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)
    session_storage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "url": self.url,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
        }


class StateManager:
    def __init__(self) -> None:
        self._snapshots: dict[str, BrowserStateSnapshot] = {}

    async def snapshot(self, session: Any, state_id: str) -> BrowserStateSnapshot:
        url = await read_current_url(session)
        cookies = await self._get_cookies(session)
        local_storage = await self._get_storage(session, "localStorage")
        session_storage = await self._get_storage(session, "sessionStorage")
        snap = BrowserStateSnapshot(
            state_id=state_id,
            url=url,
            cookies=cookies,
            local_storage=local_storage,
            session_storage=session_storage,
        )
        self._snapshots[state_id] = snap
        return snap

    async def restore(self, session: Any, state_id: str) -> bool:
        snap = self._snapshots.get(state_id)
        if snap is None:
            return False
        await self._set_cookies(session, snap.cookies)
        await self._set_storage(session, "localStorage", snap.local_storage)
        await self._set_storage(session, "sessionStorage", snap.session_storage)
        await session.navigate_to(snap.url)
        return True

    def list_states(self) -> list[str]:
        return list(self._snapshots.keys())

    def get(self, state_id: str) -> BrowserStateSnapshot | None:
        return self._snapshots.get(state_id)

    async def _get_cookies(self, session: Any) -> list[dict[str, Any]]:
        try:
            cdp = await session.get_or_create_cdp_session(target_id=None, focus=True)
            result = await cdp.cdp_client.send.Network.getCookies(session_id=cdp.session_id)
            return result.get("cookies", [])
        except Exception:
            return []

    async def _set_cookies(self, session: Any, cookies: list[dict[str, Any]]) -> None:
        if not cookies:
            return
        try:
            cdp = await session.get_or_create_cdp_session(target_id=None, focus=True)
            await cdp.cdp_client.send.Network.setCookies(
                params={"cookies": cookies},
                session_id=cdp.session_id,
            )
        except Exception:
            pass

    async def _get_storage(self, session: Any, kind: str) -> dict[str, str]:
        raw = await evaluate_js(
            session,
            f"""
            (() => {{
              const s = window.{kind};
              const out = {{}};
              for (let i = 0; i < s.length; i++) {{
                const k = s.key(i);
                out[k] = s.getItem(k);
              }}
              return out;
            }})()
            """,
        )
        return raw if isinstance(raw, dict) else {}

    async def _set_storage(self, session: Any, kind: str, data: dict[str, str]) -> None:
        payload = json.dumps(data)
        await evaluate_js(
            session,
            f"""
            (() => {{
              const s = window.{kind};
              s.clear();
              const data = {payload};
              for (const [k, v] of Object.entries(data)) s.setItem(k, v);
              return true;
            }})()
            """,
        )
