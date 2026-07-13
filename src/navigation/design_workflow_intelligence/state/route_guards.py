"""Phase 2: detect route guards and annotate prerequisites."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from navigation.visual_browser_intelligence.actions.scripted_actions import click_button_text, click_link_text, set_input_by_label
from navigation.visual_browser_intelligence.verify.verification import read_current_url


@dataclass(slots=True)
class RouteGuard:
    route: str
    accessible: bool
    redirected_to: str | None = None
    requires_auth: bool = False
    requires_role: str | None = None
    prerequisite_state: str | None = None

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "accessible": self.accessible,
            "redirected_to": self.redirected_to,
            "requires_auth": self.requires_auth,
            "requires_role": self.requires_role,
            "prerequisite_state": self.prerequisite_state,
        }


@dataclass(slots=True)
class GuardProbeResult:
    ok: bool
    guards: list[RouteGuard] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "guards": [g.to_dict() for g in self.guards],
            "error": self.error,
        }


async def probe_route_guard(
    session: Any,
    base_url: str,
    route: str,
    *,
    expected_redirect: str | None = None,
    requires_auth: bool = False,
    requires_role: str | None = None,
) -> RouteGuard:
    b = base_url.rstrip("/")
    target = route if route.startswith("http") else f"{b}{route}"
    await session.navigate_to(target)
    url = await read_current_url(session)
    redirected = url if url.rstrip("/") != target.rstrip("/") else None
    accessible = redirected is None

    if expected_redirect and expected_redirect.lower() not in url.lower():
        accessible = False

    prereq = None
    if requires_auth:
        prereq = "logged_in"
    if requires_role:
        prereq = f"role_{requires_role}"

    return RouteGuard(
        route=route,
        accessible=accessible,
        redirected_to=redirected,
        requires_auth=requires_auth,
        requires_role=requires_role,
        prerequisite_state=prereq,
    )


async def login_as_admin(session: Any, base_url: str) -> None:
    b = base_url.rstrip("/")
    await session.navigate_to(f"{b}/login")
    await set_input_by_label(session, "Username", "admin")
    await set_input_by_label(session, "Password", "1234")
    await click_button_text(session, "Continue")
    await asyncio.sleep(0.5)


async def probe_maze_guards(session: Any, base_url: str, *, restore_url: bool = True) -> GuardProbeResult:
    """Probe guards without full reload after login (SPA auth is in-memory)."""
    guards: list[RouteGuard] = []
    url_before = await read_current_url(session)
    try:
        # Anonymous: full navigation reloads app → no auth → redirect
        g1 = await probe_route_guard(
            session, base_url, "/dashboard",
            expected_redirect="/login",
            requires_auth=True,
        )
        guards.append(g1)

        await login_as_admin(session, base_url)
        url_after_login = await read_current_url(session)
        g2 = RouteGuard(
            route="/dashboard",
            accessible="/dashboard" in url_after_login,
            redirected_to=None if "/dashboard" in url_after_login else url_after_login,
            requires_auth=True,
            prerequisite_state="logged_in",
        )
        guards.append(g2)

        # In-app navigation only — navigate_to would wipe SPA auth
        await click_link_text(session, "Admin (restricted)")
        await asyncio.sleep(0.4)
        url_admin = await read_current_url(session)
        g3 = RouteGuard(
            route="/dashboard/reports/admin",
            accessible="/dashboard/reports/admin" in url_admin,
            redirected_to=None if "/dashboard/reports/admin" in url_admin else url_admin,
            requires_auth=True,
            requires_role="admin",
            prerequisite_state="role_admin",
        )
        guards.append(g3)

        ok = (
            not g1.accessible
            and g1.redirected_to is not None
            and "/login" in g1.redirected_to
            and g2.accessible
            and g3.accessible
        )
        result = GuardProbeResult(ok=ok, guards=guards)
        if restore_url and url_before:
            await session.navigate_to(url_before)
        return result
    except Exception as exc:
        if restore_url and url_before:
            try:
                await session.navigate_to(url_before)
            except Exception:
                pass
        return GuardProbeResult(ok=False, guards=guards, error=str(exc))
