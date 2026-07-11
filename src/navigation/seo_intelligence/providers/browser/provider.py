"""Browser Intelligence SEO adapter — reuses visual_browser_intelligence, does not duplicate browser."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta


class BrowserSeoProvider:
	provider_id = 'browser'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		if not request.scan_id:
			return 'not_configured', ['browser_seo_requires_scan_id:run_perception_observe_first']
		return 'pending_auth', ['browser_seo_adapter_research_phase']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		degraded = ['browser_seo_adapter_research_phase']
		if not request.scan_id:
			degraded.append('no_scan_id_for_browser_evidence')
		return [], degraded
