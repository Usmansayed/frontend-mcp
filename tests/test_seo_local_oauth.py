"""Local OAuth callback server tests."""
from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence.auth.local_server import await_oauth_callback
from navigation.seo_intelligence.config.defaults import (
	google_oauth_redirect_uri,
	oauth_callback_parts_from_redirect_uri,
)


def test_oauth_callback_receives_code() -> None:
	redirect_uri = google_oauth_redirect_uri()
	callback_path, port = oauth_callback_parts_from_redirect_uri(redirect_uri)

	async def _run() -> str:
		wait_task = asyncio.create_task(
			await_oauth_callback(callback_path=callback_path, port=port),
		)
		await asyncio.sleep(0.1)

		def hit_callback() -> None:
			urlopen(f'http://localhost:{port}{callback_path}?code=test-auth-code', timeout=5)

		threading.Thread(target=hit_callback, daemon=True).start()
		code, used_redirect = await wait_task
		assert code == 'test-auth-code'
		assert used_redirect == redirect_uri
		return code

	asyncio.run(_run())


def test_google_redirect_uri_default() -> None:
	uri = google_oauth_redirect_uri()
	assert uri == 'http://localhost:5000/api/auth/google/callback'


def test_connect_google_browser_flow_mocked() -> None:
	from unittest.mock import AsyncMock, patch

	from navigation.seo_intelligence.auth.connect import connect_google
	from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

	mock_onboarding = AsyncMock()
	mock_onboarding.complete_google_connect = AsyncMock(
		return_value={
			'website_url': 'https://example.com/',
			'provider': 'google',
			'step': 'ready',
			'profile': {'google_connected': True},
			'discovery_notes': [],
		}
	)

	async def _run() -> None:
		with (
			patch('navigation.seo_intelligence.auth.connect.run_browser_oauth', new=AsyncMock(return_value=('code-1', 'http://localhost:5000/api/auth/google/callback'))),
			patch('navigation.seo_intelligence.auth.connect.google_api.google_oauth_configured', return_value=True),
			patch('navigation.seo_intelligence.auth.connect.google_api.build_authorization_url', return_value='https://accounts.google.com/o/oauth2/auth'),
		):
			result = await connect_google('https://example.com', open_browser=False, onboarding=mock_onboarding)
		assert result['step'] == 'ready'
		mock_onboarding.complete_google_connect.assert_awaited_once()

	asyncio.run(_run())
