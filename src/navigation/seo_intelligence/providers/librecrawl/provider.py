"""LibreCrawl provider — technical SEO crawl adapter."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.librecrawl.client import LibreCrawlClient, base_url
from navigation.seo_intelligence.providers.librecrawl.normalize import normalize_crawl_payload


class LibreCrawlProvider:
	provider_id = 'librecrawl'

	def __init__(self, client: LibreCrawlClient | None = None) -> None:
		self._client = client

	def _api(self) -> LibreCrawlClient:
		return self._client or LibreCrawlClient()

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		if not base_url():
			return 'not_configured', ['librecrawl_base_url_missing:set_LIBRECRAWL_BASE_URL']
		client = self._api()
		payload, degraded = await client.crawl_status()
		if payload is not None:
			return 'connected', degraded
		return 'degraded', degraded

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		client = self._api()
		if not client.configured():
			return [], ['librecrawl_not_configured']

		url = request.website_url.strip()
		if not url:
			return [], ['librecrawl_website_url_missing']

		payload, degraded = await client.crawl_site(url)
		if payload is None:
			return [], degraded or ['librecrawl_crawl_failed']
		evidence = normalize_crawl_payload(payload)
		if not evidence:
			degraded.append('librecrawl_no_issues_found')
		return evidence, degraded
