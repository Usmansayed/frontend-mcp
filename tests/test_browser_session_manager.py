"""Unit tests for BrowserSessionManager — ref counting and reuse without launching Chromium."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navigation.visual_browser_intelligence.browser.browser_session_manager import BrowserSessionManager
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


@pytest.fixture
def manager() -> BrowserSessionManager:
    BrowserSessionManager.reset_default()
    return BrowserSessionManager(idle_timeout_s=60.0)


@pytest.fixture
def mock_browser() -> MagicMock:
    browser = MagicMock()
    browser.is_running = AsyncMock(return_value=True)
    browser.kill = AsyncMock()
    browser.navigate_to = AsyncMock()
    return browser


@pytest.mark.asyncio
async def test_acquire_reuses_alive_browser(manager: BrowserSessionManager, mock_browser: MagicMock) -> None:
    launch_count = 0

    async def fake_launch(**kwargs: object) -> object:
        nonlocal launch_count
        launch_count += 1
        from navigation.visual_browser_intelligence.browser.browser_session_manager import ManagedBrowser

        return ManagedBrowser(
            browser=mock_browser,
            headless=kwargs.get("headless", True),
            viewport_width=1920,
            viewport_height=1080,
            base_url=str(kwargs.get("base_url", "")),
        )

    with patch.object(manager, "_launch", side_effect=fake_launch):
        first = await manager.acquire(base_url="http://localhost:5173", headless=True)
        second = await manager.acquire(base_url="http://localhost:5173", headless=True)

    assert first.browser is second.browser
    assert launch_count == 1
    assert manager.ref_count == 2


@pytest.mark.asyncio
async def test_release_schedules_idle_not_immediate_kill(manager: BrowserSessionManager, mock_browser: MagicMock) -> None:
    managed = MagicMock()
    managed.browser = mock_browser
    managed.headless = True
    managed.viewport_width = 1920
    managed.viewport_height = 1080
    managed.base_url = "http://localhost:5173"
    managed.console = MagicMock(detach=MagicMock())
    managed.network = MagicMock(detach=MagicMock())
    manager._managed = managed  # noqa: SLF001
    manager._ref_count = 1

    await manager.release()
    assert manager.ref_count == 0
    mock_browser.kill.assert_not_called()


@pytest.mark.asyncio
async def test_end_all_kills_browser(manager: BrowserSessionManager, mock_browser: MagicMock) -> None:
    from navigation.visual_browser_intelligence.browser.browser_session_manager import ManagedBrowser

    manager._managed = ManagedBrowser(  # noqa: SLF001
        browser=mock_browser,
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        base_url="http://localhost:5173",
        console=MagicMock(detach=MagicMock()),
        network=MagicMock(detach=MagicMock()),
    )
    manager._ref_count = 2

    await manager.end_all()
    mock_browser.kill.assert_called_once()
    assert manager._managed is None
    assert manager.ref_count == 0


@pytest.mark.asyncio
async def test_session_store_shares_manager_browser() -> None:
    BrowserSessionManager.reset_default()
    mgr = BrowserSessionManager(idle_timeout_s=60.0)
    store = SessionStore(manager=mgr)

    mock_browser = MagicMock()
    mock_browser.is_running = AsyncMock(return_value=True)
    mock_browser.kill = AsyncMock()
    mock_browser.navigate_to = AsyncMock()

    from navigation.visual_browser_intelligence.browser.browser_session_manager import ManagedBrowser

    managed = ManagedBrowser(
        browser=mock_browser,
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        base_url="http://localhost:5173",
        console=MagicMock(),
        network=MagicMock(),
    )

    with patch.object(mgr, "acquire", AsyncMock(return_value=managed)) as acquire:
        rec1 = await store.start(base_url="http://localhost:5173", headless=True)
        rec2 = await store.start(base_url="http://localhost:5173", headless=True)

    assert acquire.await_count == 2
    assert rec1.browser is rec2.browser

    with patch.object(mgr, "release", AsyncMock()) as release:
        await store.end(rec1.session_id)
        await store.end(rec2.session_id)

    assert release.await_count == 2


@pytest.mark.asyncio
async def test_profile_mismatch_with_active_refs_uses_isolated(
    manager: BrowserSessionManager, mock_browser: MagicMock
) -> None:
    from navigation.visual_browser_intelligence.browser.browser_session_manager import ManagedBrowser

    shared = ManagedBrowser(
        browser=mock_browser,
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        base_url="http://localhost:5173",
        console=MagicMock(detach=MagicMock()),
        network=MagicMock(detach=MagicMock()),
    )
    manager._managed = shared  # noqa: SLF001
    manager._ref_count = 1

    isolated_browser = MagicMock()
    isolated_browser.is_running = AsyncMock(return_value=True)
    isolated_browser.kill = AsyncMock()

    with patch.object(
        manager,
        "_launch",
        AsyncMock(
            return_value=ManagedBrowser(
                browser=isolated_browser,
                headless=False,
                viewport_width=1440,
                viewport_height=900,
                base_url="https://dribbble.com",
                console=MagicMock(),
                network=MagicMock(),
            )
        ),
    ) as launch:
        acquired = await manager.acquire(
            base_url="https://dribbble.com",
            headless=False,
            viewport_width=1440,
            viewport_height=900,
        )

    mock_browser.kill.assert_not_called()
    launch.assert_awaited_once()
    assert acquired.browser is isolated_browser
    assert manager._managed.browser is mock_browser  # noqa: SLF001
    assert manager.ref_count == 1


@pytest.mark.asyncio
async def test_profile_mismatch_relaunches(manager: BrowserSessionManager, mock_browser: MagicMock) -> None:
    from navigation.visual_browser_intelligence.browser.browser_session_manager import ManagedBrowser

    old_browser = MagicMock()
    old_browser.is_running = AsyncMock(return_value=True)
    old_browser.kill = AsyncMock()
    manager._managed = ManagedBrowser(  # noqa: SLF001
        browser=old_browser,
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        base_url="http://localhost:5173",
        console=MagicMock(detach=MagicMock()),
        network=MagicMock(detach=MagicMock()),
    )
    manager._ref_count = 0

    with patch.object(manager, "_launch", AsyncMock(return_value=ManagedBrowser(
        browser=mock_browser,
        headless=False,
        viewport_width=1440,
        viewport_height=900,
        base_url="https://dribbble.com",
        console=MagicMock(),
        network=MagicMock(),
    ))):
        acquired = await manager.acquire(
            base_url="https://dribbble.com",
            headless=False,
            viewport_width=1440,
            viewport_height=900,
        )

    old_browser.kill.assert_called_once()
    assert acquired.browser is mock_browser
