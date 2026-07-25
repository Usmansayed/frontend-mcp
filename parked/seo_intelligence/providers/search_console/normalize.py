"""Normalize Google Search Console API payloads to SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef

_MAX_ROWS = 50


def normalize_search_analytics(
	payload: dict[str, Any],
	*,
	site_url: str,
	provider_id: str = 'search-console',
	dimensions: list[str] | None = None,
) -> list[SeoEvidenceRef]:
	rows = payload.get('rows') or []
	evidence: list[SeoEvidenceRef] = []
	dims = dimensions or ['query']
	for row in rows[:_MAX_ROWS]:
		keys = row.get('keys') or []
		label = ' / '.join(str(k) for k in keys) if keys else '(aggregate)'
		clicks = int(row.get('clicks') or 0)
		impressions = int(row.get('impressions') or 0)
		ctr = float(row.get('ctr') or 0.0)
		position = float(row.get('position') or 0.0)
		page_dim = ''
		if len(keys) >= 2 and 'page' in dims:
			page_dim = str(keys[1])
		elif len(keys) >= 1 and dims == ['page']:
			page_dim = str(keys[0])
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.SEARCH_QUERY.value,
					title=label,
					source_ref='searchanalytics.query',
					metric_key=label,
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.SEARCH_QUERY,
				title=label,
				summary=(
					f'{clicks} clicks, {impressions} impressions, '
					f'CTR {ctr * 100:.1f}%, avg position {position:.1f}'
				),
				url=site_url,
				page_url=page_dim,
				metric_value=position,
				metric_unit='position',
				severity='info',
				source_ref='searchanalytics.query',
				metadata={
					'clicks': clicks,
					'impressions': impressions,
					'ctr': ctr,
					'keys': keys,
					'dimensions': dims,
					'landingPage': page_dim,
				},
			)
		)
	return evidence


def normalize_url_inspection(
	payload: dict[str, Any],
	*,
	site_url: str,
	inspection_url: str,
	provider_id: str = 'search-console',
	index: int = 0,
) -> list[SeoEvidenceRef]:
	result = payload.get('inspectionResult') or {}
	index_status = result.get('indexStatusResult') or {}
	verdict = str(index_status.get('verdict') or 'UNKNOWN')
	coverage = str(index_status.get('coverageState') or '—')
	google_canonical = index_status.get('googleCanonical')
	user_canonical = index_status.get('userCanonical')
	summary_parts = [f'{verdict}: {coverage}']
	if google_canonical:
		summary_parts.append(f'Google canonical: {google_canonical}')
	if user_canonical and user_canonical != google_canonical:
		summary_parts.append(f'Declared canonical: {user_canonical}')

	severity = {
		'PASS': 'info',
		'NEUTRAL': 'info',
		'PARTIAL': 'medium',
		'FAIL': 'high',
	}.get(verdict, 'medium')

	return [
		SeoEvidenceRef(
			evidence_id=stable_evidence_id(
				provider_id,
				SeoEvidenceKind.INDEX_STATUS.value,
				page_url=inspection_url,
				source_ref='urlInspection.index',
			),
			provider_id=provider_id,
			kind=SeoEvidenceKind.INDEX_STATUS,
			title=f'Index status: {inspection_url}',
			summary='; '.join(summary_parts),
			url=site_url,
			page_url=inspection_url,
			severity=severity,
			source_ref='urlInspection.index',
			metadata={
				'verdict': verdict,
				'coverageState': coverage,
				'indexStatusResult': index_status,
			},
		)
	]
