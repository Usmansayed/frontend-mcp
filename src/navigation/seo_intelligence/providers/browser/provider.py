"""Browser Intelligence SEO adapter — reuses visual_browser_intelligence via ScanRegistry."""
from __future__ import annotations

from typing import TYPE_CHECKING

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.browser.normalize import normalize_browser_observation

if TYPE_CHECKING:
	from navigation.core.scan_registry import ScanRegistry


class BrowserSeoProvider:
	provider_id = 'browser'

	def __init__(self, scan_registry: ScanRegistry | None = None) -> None:
		self._scans = scan_registry

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		if not request.scan_id:
			return 'not_configured', ['browser_seo_requires_scan_id:run_perception_observe_first']
		if self._scans is None:
			return 'pending_auth', ['browser_scan_registry_unavailable']
		record = self._scans.get(request.scan_id)
		if record is None:
			return 'error', [f'browser_scan_not_found:{request.scan_id}']
		return 'connected', []

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		if not request.scan_id:
			return [], ['no_scan_id_for_browser_evidence']
		if self._scans is None:
			return [], ['browser_scan_registry_unavailable']
		record = self._scans.get(request.scan_id)
		if record is None:
			return [], [f'browser_scan_not_found:{request.scan_id}']
		evidence = normalize_browser_observation(
			record.observation,
			scan_id=request.scan_id,
		)
		degraded: list[str] = []
		if not evidence:
			degraded.append('browser_no_seo_evidence_from_scan')
		return evidence, degraded

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]
