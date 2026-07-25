"""Tests for LibreCrawl companion service lifecycle."""

from __future__ import annotations



import asyncio

import sys

from pathlib import Path

from unittest.mock import AsyncMock, patch



ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / 'src'))



from navigation.seo_intelligence.setup.companion_services import (

	CompanionStatus,

	ensure_companion,

	probe_librecrawl,

)





def test_probe_librecrawl_healthy_when_api_ok() -> None:

	async def _run() -> None:

		with patch(

			'navigation.seo_intelligence.setup.companion_services.LibreCrawlClient.crawl_status',

			new=AsyncMock(return_value=({'status': 'idle'}, [])),

		):

			status = await probe_librecrawl()

		assert status.healthy is True

		assert status.service_id == 'librecrawl'



	asyncio.run(_run())





def test_ensure_companion_skips_start_when_already_healthy() -> None:

	async def _run() -> None:

		healthy = CompanionStatus('librecrawl', 'http://localhost:5001', True, running=True)

		with patch(

			'navigation.seo_intelligence.setup.companion_services.probe_librecrawl',

			new=AsyncMock(return_value=healthy),

		):

			with patch(

				'navigation.seo_intelligence.setup.companion_services.start_companion_process',

			) as start_mock:

				result = await ensure_companion('librecrawl')

		assert result.healthy is True

		start_mock.assert_not_called()



	asyncio.run(_run())





def test_ensure_companion_starts_when_unhealthy() -> None:

	async def _run() -> None:

		unhealthy = CompanionStatus('librecrawl', 'http://localhost:5001', False, diagnostic='down')

		healthy = CompanionStatus('librecrawl', 'http://localhost:5001', True, running=True)

		with (

			patch(

				'navigation.seo_intelligence.setup.companion_services.probe_librecrawl',

				new=AsyncMock(side_effect=[unhealthy, healthy]),

			),

			patch(

				'navigation.seo_intelligence.setup.companion_services.asyncio.to_thread',

				new=AsyncMock(side_effect=lambda fn, *args: fn(*args)),

			),

			patch(

				'navigation.seo_intelligence.setup.companion_services.start_companion_process',

				return_value=(True, ['librecrawl_started:pid_1']),

			) as start_mock_sync,

		):

			result = await ensure_companion('librecrawl')

		assert result.healthy is True

		start_mock_sync.assert_called_once_with('librecrawl')

		assert 'librecrawl_started:pid_1' in result.notes



	asyncio.run(_run())


