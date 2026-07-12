"""SEO provider manager — routes to live adapters."""
from __future__ import annotations

from typing import TYPE_CHECKING

from navigation.seo_intelligence.providers.analytics.provider import Ga4Provider
from navigation.seo_intelligence.providers.bing.provider import BingWebmasterProvider
from navigation.seo_intelligence.providers.browser.provider import BrowserSeoProvider
from navigation.seo_intelligence.providers.librecrawl.provider import LibreCrawlProvider
from navigation.seo_intelligence.providers.lighthouse.provider import LighthouseProvider
from navigation.seo_intelligence.providers.protocol import SeoDataProvider
from navigation.seo_intelligence.providers.search_console.provider import SearchConsoleProvider

if TYPE_CHECKING:
	from navigation.core.scan_registry import ScanRegistry


class SeoProviderManager:
	def __init__(self, *, scan_registry: ScanRegistry | None = None) -> None:
		self._scan_registry = scan_registry
		self._providers: dict[str, SeoDataProvider] = {
			'search-console': SearchConsoleProvider(),
			'analytics-ga4': Ga4Provider(),
			'bing-webmaster': BingWebmasterProvider(),
			'librecrawl': LibreCrawlProvider(),
			'lighthouse': LighthouseProvider(),
			'browser': BrowserSeoProvider(scan_registry=scan_registry),
		}

	def get(self, provider_id: str) -> SeoDataProvider | None:
		return self._providers.get(provider_id)

	def list_live_provider_ids(self) -> list[str]:
		return sorted(self._providers.keys())
