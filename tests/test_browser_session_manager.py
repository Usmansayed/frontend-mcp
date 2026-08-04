"""Browser Session Manager — single-browser lifecycle + recovery tests."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navigation.visual_browser_intelligence.browser.browser_session_manager import (
    BrowserSessionManager,
    ManagedBrowser,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


def _live_browser() -> MagicMock:
    browser = MagicMock()
    browser.is_running = AsyncMock(return_value=True)
    browser.is_cdp_connected = True
    browser.kill = AsyncMock()
    browser.navigate_to = AsyncMock()
    browser.get_tabs = MagicMock(return_value=[{"id": "1"}])
    return browser


def _dead_browser() -> MagicMock:
    browser = MagicMock()
    browser.is_running = AsyncMock(return_value=False)
    browser.is_cdp_connected = False
    browser.kill = AsyncMock()
    browser.navigate_to = AsyncMock()
    return browser


def _managed(browser: MagicMock, **kwargs: object) -> ManagedBrowser:
    return ManagedBrowser(
        browser=browser,
        headless=bool(kwargs.get("headless", True)),
        viewport_width=int(kwargs.get("viewport_width", 1920)),  # type: ignore[arg-type]
        viewport_height=int(kwargs.get("viewport_height", 1080)),  # type: ignore[arg-type]
        base_url=str(kwargs.get("base_url", "")),
        console=MagicMock(detach=MagicMock(), attach=AsyncMock()),
        network=MagicMock(detach=MagicMock(), attach=AsyncMock()),
    )


@pytest.fixture
def manager() -> BrowserSessionManager:
    BrowserSessionManager.reset_default()
    return BrowserSessionManager(idle_timeout_s=60.0)


@pytest.mark.asyncio
async def test_acquire_reuses_alive_browser(manager: BrowserSessionManager) -> None:
    launch_count = 0
    mock_browser = _live_browser()

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        nonlocal launch_count
        launch_count += 1
        return _managed(mock_browser, **kwargs)

    with patch.object(manager, "_launch", side_effect=fake_launch):
        first = await manager.acquire(base_url="http://localhost:5173", headless=True)
        second = await manager.acquire(base_url="http://localhost:5173", headless=True)

    assert first.browser is second.browser
    assert first.browser_id == second.browser_id
    assert launch_count == 1
    assert manager.ref_count == 2


@pytest.mark.asyncio
async def test_fifty_consecutive_acquires_single_launch(manager: BrowserSessionManager) -> None:
    launch_count = 0
    mock_browser = _live_browser()

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        nonlocal launch_count
        launch_count += 1
        return _managed(mock_browser, **kwargs)

    with patch.object(manager, "_launch", side_effect=fake_launch):
        for _ in range(50):
            await manager.acquire(base_url="http://localhost:5173", headless=True)
        for _ in range(50):
            await manager.release()

    assert launch_count == 1
    assert manager.ref_count == 0
    diag = manager.diagnostics()
    assert diag["restart_count"] == 0
    assert diag["isolated_browsers"] == 0


@pytest.mark.asyncio
async def test_profile_mismatch_reuses_primary_not_isolate(
    manager: BrowserSessionManager,
) -> None:
    """Inspiration headed/viewport mismatch must NOT spawn a second Chromium."""
    shared_browser = _live_browser()
    shared = _managed(
        shared_browser,
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        base_url="http://localhost:5173",
    )
    manager._managed = shared  # noqa: SLF001
    manager._ref_count = 1

    with patch.object(manager, "_launch", AsyncMock()) as launch:
        acquired = await manager.acquire(
            base_url="https://dribbble.com",
            headless=False,
            viewport_width=1440,
            viewport_height=900,
        )

    launch.assert_not_awaited()
    assert acquired.browser is shared_browser
    assert manager.ref_count == 2
    assert manager.diagnostics()["isolated_browsers"] == 0


@pytest.mark.asyncio
async def test_user_close_recovers_on_next_acquire(manager: BrowserSessionManager) -> None:
    dead = _dead_browser()
    alive = _live_browser()
    manager._managed = _managed(dead, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 1

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        return _managed(alive, **kwargs)

    with patch.object(manager, "_launch", side_effect=fake_launch):
        acquired = await manager.acquire(base_url="http://localhost:5173", headless=True)

    assert acquired.browser is alive
    assert manager.restart_count == 1
    assert manager._last_close_reason in ("acquire", "user_closed")  # noqa: SLF001


@pytest.mark.asyncio
async def test_ensure_alive_rebinds_after_disconnect(manager: BrowserSessionManager) -> None:
    dead = _dead_browser()
    alive = _live_browser()
    manager._managed = _managed(dead, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 1
    manager.register_logical_session("sess_abc")

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        return _managed(alive, **kwargs)

    with patch.object(manager, "_launch", side_effect=fake_launch):
        recovered = await manager.ensure_alive(base_url="http://localhost:5173")

    assert recovered is not None
    assert recovered.browser is alive
    assert manager.restart_count == 1
    assert manager.diagnostics()["restart_count"] == 1


@pytest.mark.asyncio
async def test_session_store_ensure_rebounds_browser() -> None:
    BrowserSessionManager.reset_default()
    mgr = BrowserSessionManager(idle_timeout_s=60.0)
    store = SessionStore(manager=mgr)

    dead = _dead_browser()
    alive = _live_browser()
    first = _managed(dead, base_url="http://localhost:5173")
    second = _managed(alive, base_url="http://localhost:5173")

    with patch.object(mgr, "acquire", AsyncMock(return_value=first)):
        rec = await store.start(base_url="http://localhost:5173", headless=True)

    with patch.object(mgr, "ensure_alive", AsyncMock(return_value=second)):
        ensured = await store.ensure(rec.session_id)

    assert ensured.browser is alive
    assert ensured._manager_browser_id == second.browser_id  # noqa: SLF001


@pytest.mark.asyncio
async def test_release_schedules_idle_not_immediate_kill(manager: BrowserSessionManager) -> None:
    mock_browser = _live_browser()
    manager._managed = _managed(mock_browser, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 1

    await manager.release()
    assert manager.ref_count == 0
    mock_browser.kill.assert_not_called()


@pytest.mark.asyncio
async def test_end_all_kills_browser(manager: BrowserSessionManager) -> None:
    mock_browser = _live_browser()
    manager._managed = _managed(mock_browser, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 2
    manager.register_logical_session("sess_1")

    await manager.end_all()
    mock_browser.kill.assert_called_once()
    assert manager._managed is None  # noqa: SLF001
    assert manager.ref_count == 0
    assert manager.diagnostics()["active_sessions"] == 0
    assert manager.diagnostics()["last_close_reason"] == "process_shutdown"


@pytest.mark.asyncio
async def test_idle_timeout_kills_when_idle() -> None:
    BrowserSessionManager.reset_default()
    manager = BrowserSessionManager(idle_timeout_s=0.05)
    mock_browser = _live_browser()
    manager._managed = _managed(mock_browser, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 1

    await manager.release()
    await asyncio.sleep(0.15)
    mock_browser.kill.assert_called()
    assert manager._managed is None  # noqa: SLF001
    assert manager.diagnostics()["last_close_reason"] == "idle_timeout"


@pytest.mark.asyncio
async def test_inspiration_and_mcp_share_one_browser() -> None:
    """MCP headless session + inspiration headed request → one physical browser."""
    BrowserSessionManager.reset_default()
    mgr = BrowserSessionManager(idle_timeout_s=60.0)
    mcp_store = SessionStore(manager=mgr)
    insp_store = SessionStore(manager=mgr)

    launch_count = 0
    browser = _live_browser()

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        nonlocal launch_count
        launch_count += 1
        return _managed(browser, **kwargs)

    with patch.object(mgr, "_launch", side_effect=fake_launch):
        mcp = await mcp_store.start(base_url="http://localhost:5173", headless=True)
        insp = await insp_store.start(
            base_url="https://dribbble.com",
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
        )

    assert launch_count == 1
    assert mcp.browser is insp.browser
    assert mgr.diagnostics()["isolated_browsers"] == 0
    assert mgr.diagnostics()["active_sessions"] == 2

    await mcp_store.end(mcp.session_id)
    await insp_store.end(insp.session_id)
    assert mgr.ref_count == 0


@pytest.mark.asyncio
async def test_diagnostics_shape(manager: BrowserSessionManager) -> None:
    browser = _live_browser()
    manager._managed = _managed(browser, base_url="http://localhost:5173")  # noqa: SLF001
    manager._ref_count = 1
    manager.register_logical_session("sess_x")

    diag = manager.diagnostics()
    assert "browser_running" in diag
    assert "browser_connected" in diag
    assert "browser_id" in diag
    assert diag["active_sessions"] == 1
    assert diag["active_leases"] == 1
    assert diag["restart_count"] == 0
    assert diag["isolated_browsers"] == 0


@pytest.mark.asyncio
async def test_park_and_restore_verifies_live_url(manager: BrowserSessionManager) -> None:
    """Guest tools must restore app URL; restored=true only when live origin matches."""
    browser = _live_browser()
    live_url = {"value": "http://localhost:5173/dashboard"}

    async def fake_read(_b: object) -> str:
        return live_url["value"]

    async def fake_nav(url: str) -> None:
        live_url["value"] = url

    browser.navigate_to = AsyncMock(side_effect=fake_nav)
    managed = _managed(browser, base_url="http://localhost:5173")
    managed.app_base_url = "http://localhost:5173"
    manager._managed = managed  # noqa: SLF001
    manager._ref_count = 1

    with patch(
        "navigation.visual_browser_intelligence.verify.verification.read_current_url",
        side_effect=fake_read,
    ):
        parked = await manager.park_current_url(app_base_url="http://localhost:5173")
        assert parked == "http://localhost:5173/dashboard"
        assert managed.parked_url == parked

        # Guest navigates away
        await browser.navigate_to("https://dribbble.com/search")
        assert live_url["value"] == "https://dribbble.com/search"

        result = await manager.restore_parked_url()
        assert result["attempted"] is True
        assert result["restored"] is True
        assert live_url["value"] == "http://localhost:5173/dashboard"
        assert managed.parked_url == ""


@pytest.mark.asyncio
async def test_ensure_on_app_origin_when_stuck_on_external(
    manager: BrowserSessionManager,
) -> None:
    browser = _live_browser()
    live_url = {"value": "https://www.awwwards.com/websites/"}

    async def fake_read(_b: object) -> str:
        return live_url["value"]

    async def fake_nav(url: str) -> None:
        live_url["value"] = url

    browser.navigate_to = AsyncMock(side_effect=fake_nav)
    managed = _managed(browser, base_url="http://localhost:5173")
    managed.app_base_url = "http://localhost:5173"
    manager._managed = managed  # noqa: SLF001
    manager._ref_count = 1

    with patch(
        "navigation.visual_browser_intelligence.verify.verification.read_current_url",
        side_effect=fake_read,
    ):
        out = await manager.ensure_on_app_origin(
            app_base_url="http://localhost:5173",
            preferred_url="http://localhost:5173/app",
        )
        assert out["checked"] is True
        assert out["restored"] is True
        assert live_url["value"] == "http://localhost:5173/app"


@pytest.mark.asyncio
async def test_same_origin_helper() -> None:
    from navigation.visual_browser_intelligence.browser.browser_session_manager import (
        same_origin,
    )

    assert same_origin("http://localhost:5173/a", "http://localhost:5173/b")
    assert not same_origin("http://localhost:5173/", "https://dribbble.com/")
    assert not same_origin("", "http://localhost:5173/")


@pytest.mark.asyncio
async def test_isolated_ignored_without_env(manager: BrowserSessionManager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERCEPTION_ALLOW_ISOLATED_BROWSER", raising=False)
    manager._allow_isolated = False
    browser = _live_browser()
    launch_count = 0

    async def fake_launch(**kwargs: object) -> ManagedBrowser:
        nonlocal launch_count
        launch_count += 1
        return _managed(browser, **kwargs)

    with patch.object(manager, "_launch", side_effect=fake_launch):
        a = await manager.acquire(base_url="http://localhost:5173", headless=True)
        b = await manager.acquire(
            base_url="https://figma.com",
            headless=False,
            isolated=True,
        )

    assert a.browser is b.browser
    assert launch_count == 1
    assert not b.isolated
