"""Google Search Console provider — research stub (OAuth adapter Phase 1)."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class SearchConsoleProvider:
	provider_id = 'search-console'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		return 'not_configured', ['search_console_oauth_not_implemented:phase_1']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		return [], ['search_console_adapter_research_phase']
