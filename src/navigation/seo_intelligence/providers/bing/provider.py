"""Bing Webmaster Tools provider — optional research stub."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class BingWebmasterProvider:
	provider_id = 'bing-webmaster'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		return 'not_configured', ['bing_webmaster_optional:phase_2']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		return [], ['bing_webmaster_adapter_research_phase']
