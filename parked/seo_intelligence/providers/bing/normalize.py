"""Normalize Bing Webmaster API payloads to SeoEvidenceRef."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def normalize_query_stats(payload: dict[str, Any], *, site_url: str) -> tuple[list[SeoEvidenceRef], list[str]]:
	degraded: list[str] = []
	rows = payload.get('d') if isinstance(payload, dict) else None
	if not isinstance(rows, list) or not rows:
		return [], ['bing_query_stats_empty']
	evidence: list[SeoEvidenceRef] = []
	for idx, row in enumerate(rows[:50]):
		if not isinstance(row, dict):
			continue
		query = str(row.get('Query') or row.get('query') or '').strip()
		if not query:
			continue
		clicks = row.get('Clicks')
		impressions = row.get('Impressions')
		evidence.append(
			SeoEvidenceRef(
				evidence_id=f'bing_query_{idx}_{query[:40]}',
				provider_id='bing-webmaster',
				kind=SeoEvidenceKind.SEARCH_QUERY,
				title=f'Bing query: {query}',
				summary=f'clicks={clicks} impressions={impressions}',
				url=site_url,
				page_url=site_url,
				metric_value=clicks,
				metric_unit='clicks',
				severity='info',
				source_ref='bing:GetQueryStats',
				metadata={
					'query': query,
					'clicks': clicks,
					'impressions': impressions,
					'avg_click_position': row.get('AvgClickPosition'),
					'avg_impression_position': row.get('AvgImpressionPosition'),
				},
			)
		)
	if not evidence:
		degraded.append('bing_query_stats_no_rows')
	return evidence, degraded
