"""Normalize GA4 Data API reports to SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url, stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def normalize_ga4_report(
	payload: dict[str, Any],
	*,
	property_id: str,
	provider_id: str = 'analytics-ga4',
	base_url: str = '',
) -> list[SeoEvidenceRef]:
	rows = payload.get('rows') or []
	dimension_headers = [h.get('name') for h in payload.get('dimensionHeaders') or []]
	metric_headers = [h.get('name') for h in payload.get('metricHeaders') or []]
	evidence: list[SeoEvidenceRef] = []

	for row in rows[:50]:
		dim_values = [v.get('value', '') for v in row.get('dimensionValues') or []]
		metric_values = [v.get('value', '') for v in row.get('metricValues') or []]
		dims = dict(zip(dimension_headers, dim_values, strict=False))
		metrics = dict(zip(metric_headers, metric_values, strict=False))
		landing = dims.get('landingPage') or dims.get('pagePath') or '(unknown)'
		channel = dims.get('sessionDefaultChannelGroup') or ''
		sessions = _float(metrics.get('sessions'))
		users = _float(metrics.get('activeUsers'))
		conversions = _float(metrics.get('conversions'))
		engagement = _float(metrics.get('engagementRate'))
		page_url = normalize_page_url(landing, base_url=base_url) if landing.startswith('/') else landing

		title = landing if not channel else f'{landing} ({channel})'
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.TRAFFIC_METRIC.value,
					page_url=page_url or landing,
					title=title,
					source_ref='analyticsdata.runReport',
					metric_key=channel or landing,
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.TRAFFIC_METRIC,
				title=title,
				summary=(
					f'{int(sessions)} sessions, {int(users)} users, '
					f'{conversions:.1f} conversions, engagement {engagement * 100:.1f}%'
				),
				page_url=page_url or landing,
				url=property_id,
				metric_value=sessions,
				metric_unit='sessions',
				severity='info',
				source_ref='analyticsdata.runReport',
				metadata={
					'landingPage': landing,
					'channel': channel,
					'activeUsers': users,
					'conversions': conversions,
					'engagementRate': engagement,
				},
			)
		)
	return evidence


def _float(value: Any) -> float:
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0
