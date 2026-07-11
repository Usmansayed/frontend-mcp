"""Normalize OpenSEO MCP payloads into SEO Intelligence evidence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef

_MAX_QUERY_ROWS = 50
_VERDICT_SEVERITY = {
	'PASS': 'info',
	'NEUTRAL': 'info',
	'PARTIAL': 'medium',
	'FAIL': 'high',
	'VERDICT_UNSPECIFIED': 'medium',
}


def normalize_search_console_performance(
	payload: dict[str, Any],
	*,
	provider_id: str = 'openseo',
) -> tuple[list[SeoEvidenceRef], list[str]]:
	degraded: list[str] = []
	if not payload.get('ok'):
		reason = str(payload.get('reason') or 'gsc_performance_failed')
		degraded.append(f'openseo_gsc_performance:{reason}')
		return [], degraded

	rows = payload.get('rows') or []
	if not rows:
		degraded.append('openseo_gsc_performance:no_rows')
		return [], degraded

	evidence: list[SeoEvidenceRef] = []
	site_url = str(payload.get('siteUrl') or '')
	for index, row in enumerate(rows[:_MAX_QUERY_ROWS]):
		keys = row.get('keys') or []
		label = ' / '.join(str(k) for k in keys) if keys else '(aggregate)'
		clicks = int(row.get('clicks') or 0)
		impressions = int(row.get('impressions') or 0)
		ctr = float(row.get('ctr') or 0.0)
		position = float(row.get('position') or 0.0)
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'openseo:gsc:query:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.SEARCH_QUERY,
				title=label,
				summary=(
					f'{clicks} clicks, {impressions} impressions, '
					f'CTR {ctr * 100:.1f}%, avg position {position:.1f}'
				),
				url=site_url,
				metric_value=position,
				metric_unit='position',
				severity='info',
				source_ref='get_search_console_performance',
				metadata={
					'clicks': clicks,
					'impressions': impressions,
					'ctr': ctr,
					'keys': keys,
					'startDate': payload.get('startDate'),
					'endDate': payload.get('endDate'),
				},
			)
		)
	return evidence, degraded


def normalize_inspect_urls(
	payload: dict[str, Any],
	*,
	provider_id: str = 'openseo',
) -> tuple[list[SeoEvidenceRef], list[str]]:
	degraded: list[str] = []
	if not payload.get('ok'):
		reason = str(payload.get('reason') or 'url_inspection_failed')
		degraded.append(f'openseo_url_inspection:{reason}')
		return [], degraded

	results = payload.get('results') or []
	if not results:
		degraded.append('openseo_url_inspection:no_results')
		return [], degraded

	evidence: list[SeoEvidenceRef] = []
	site_url = str(payload.get('siteUrl') or '')
	for index, item in enumerate(results):
		page_url = str(item.get('url') or '')
		if item.get('error'):
			evidence.append(
				SeoEvidenceRef(
					evidence_id=f'openseo:gsc:inspect:{index}',
					provider_id=provider_id,
					kind=SeoEvidenceKind.CRAWL_ISSUE,
					title=f'Inspection failed: {page_url}',
					summary=str(item.get('error')),
					url=site_url,
					page_url=page_url,
					severity='high',
					source_ref='inspect_urls',
					metadata={'error': item.get('error')},
				)
			)
			continue

		result = item.get('result') or {}
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

		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'openseo:gsc:inspect:{index}',
				provider_id=provider_id,
				kind=SeoEvidenceKind.INDEX_STATUS,
				title=f'Index status: {page_url}',
				summary='; '.join(summary_parts),
				url=site_url,
				page_url=page_url,
				severity=_VERDICT_SEVERITY.get(verdict, 'medium'),
				source_ref='inspect_urls',
				metadata={
					'verdict': verdict,
					'coverageState': coverage,
					'indexStatusResult': index_status,
				},
			)
		)
	return evidence, degraded
