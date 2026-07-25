"""Lighthouse / PageSpeed provider — bridges frontend_quality_intelligence audits."""
from __future__ import annotations

import tempfile
from pathlib import Path

from navigation.frontend_quality_intelligence.audits.models import AuditCategory
from navigation.frontend_quality_intelligence.audits.runner import (
	LighthouseNotAvailableError,
	lighthouse_available,
	run_lighthouse,
)
from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.lighthouse.normalize import normalize_lighthouse_reports


class LighthouseProvider:
	provider_id = 'lighthouse'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		if lighthouse_available():
			return 'connected', []
		return 'not_configured', ['lighthouse_unavailable:install_node_and_npx']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		url = request.website_url.strip()
		if not url:
			return [], ['lighthouse_website_url_missing']
		if not lighthouse_available():
			return [], ['lighthouse_unavailable']

		degraded: list[str] = []
		performance_lhr: dict | None = None
		seo_lhr: dict | None = None

		with tempfile.TemporaryDirectory(prefix='seo-lh-') as tmp:
			tmp_path = Path(tmp)
			try:
				perf_out = tmp_path / 'performance.json'
				performance_lhr = await run_lighthouse(url, AuditCategory.PERFORMANCE, perf_out, tmp_dir=tmp_path)
			except LighthouseNotAvailableError:
				return [], ['lighthouse_unavailable']
			except Exception as exc:
				degraded.append(f'lighthouse_performance_error:{type(exc).__name__}')

			try:
				seo_out = tmp_path / 'seo.json'
				seo_lhr = await run_lighthouse(url, AuditCategory.SEO, seo_out, tmp_dir=tmp_path)
			except Exception as exc:
				degraded.append(f'lighthouse_seo_error:{type(exc).__name__}')

		evidence = normalize_lighthouse_reports(performance_lhr=performance_lhr, seo_lhr=seo_lhr)
		if not evidence:
			degraded.append('lighthouse_no_evidence')
		return evidence, degraded
