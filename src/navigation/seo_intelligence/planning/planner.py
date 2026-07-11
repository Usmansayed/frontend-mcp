"""SEO audit planner — route website audits to free-first providers."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoAuditRequest
from navigation.seo_intelligence.registry import SeoProviderRegistry

_DEFAULT_CHAIN = [
	'search-console',
	'analytics-ga4',
	'librecrawl',
	'lighthouse',
	'browser',
	'bing-webmaster',
]


class SeoAuditPlanner:
	def __init__(self, registry: SeoProviderRegistry | None = None) -> None:
		self._registry = registry or SeoProviderRegistry()

	def resolve_provider_ids(self, request: SeoAuditRequest) -> list[str]:
		if request.providers:
			return [pid for pid in request.providers if self._registry.get(pid) is not None]
		return [pid for pid in _DEFAULT_CHAIN if self._registry.get(pid) is not None]
