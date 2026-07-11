"""LibreCrawl provider — technical SEO crawl adapter (research stub)."""
from __future__ import annotations

import os

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class LibreCrawlProvider:
	provider_id = 'librecrawl'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		base = os.environ.get('LIBRECRAWL_BASE_URL', '').strip()
		if not base:
			return 'not_configured', ['librecrawl_base_url_missing:set_LIBRECRAWL_BASE_URL']
		return 'pending_auth', ['librecrawl_adapter_research_phase']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		return [], ['librecrawl_adapter_research_phase:do_not_build_internet_crawler']
