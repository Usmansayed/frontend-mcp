"""Shared pytest fixtures for SEO Intelligence tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from navigation.seo_intelligence.setup.companion_services import CompanionStatus


@pytest.fixture(autouse=True)
def _skip_companion_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Avoid docker/git side effects during unit tests."""
	monkeypatch.setenv('SEO_SKIP_COMPANION_BOOTSTRAP', '1')
	mock = AsyncMock(
		return_value=(
			{
				'librecrawl': CompanionStatus('librecrawl', 'http://localhost:5001', True, running=True),
			},
			[],
		)
	)
	patch('navigation.seo_intelligence.planning.orchestrator.ensure_companions_ready', mock).start()
