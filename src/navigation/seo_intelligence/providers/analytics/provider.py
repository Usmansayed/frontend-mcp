"""Google Analytics 4 provider — research stub (OAuth adapter Phase 1)."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class Ga4Provider:
	provider_id = 'analytics-ga4'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		return 'not_configured', ['ga4_oauth_not_implemented:phase_1']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		return [], ['ga4_adapter_research_phase']
