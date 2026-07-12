"""Impact scoring — traffic-weighted business priority (Sprint 2)."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef

_SEVERITY_WEIGHT = {'critical': 1.0, 'high': 0.75, 'medium': 0.45, 'low': 0.2, 'info': 0.1}
_INDEX_FAIL = frozenset({'FAIL', 'PARTIAL'})


def score_impact(
	evidence: list[SeoEvidenceRef],
	*,
	page_url: str = '',
) -> dict[str, object]:
	"""Rank recommendations by likely business impact — not fixed confidence."""
	if not evidence:
		return {'score': 0.0, 'label': 'low', 'rationale': 'no evidence'}

	target = normalize_page_url(page_url) if page_url else ''
	scope = evidence
	if target:
		scope = [
			e for e in evidence
			if normalize_page_url(page_url_for_evidence(e)) == target or not page_url_for_evidence(e)
		] or evidence

	impressions = 0.0
	clicks = 0.0
	sessions = 0.0
	severity = 0.0
	index_risk = 0.0
	http_risk = 0.0

	for item in scope:
		impressions = max(impressions, float(item.metadata.get('impressions') or 0))
		clicks = max(clicks, float(item.metadata.get('clicks') or 0))
		if item.kind.value == 'traffic_metric' and item.metric_value:
			sessions = max(sessions, float(item.metric_value))
		severity = max(severity, _SEVERITY_WEIGHT.get(item.severity, 0.1))
		verdict = str(item.metadata.get('verdict') or '')
		if item.kind.value == 'index_status' and verdict in _INDEX_FAIL:
			index_risk = 1.0
		if item.metric_unit == 'status_code' and (item.metric_value or 0) >= 400:
			http_risk = 1.0 if (item.metric_value or 0) >= 500 else 0.7

	traffic_signal = min(1.0, impressions / 2000 + clicks / 200 + sessions / 500)
	score = min(
		1.0,
		traffic_signal * 0.45
		+ severity * 0.25
		+ index_risk * 0.2
		+ http_risk * 0.1,
	)

	return {
		'score': round(score, 3),
		'label': _impact_label(score),
		'impressions_28d': int(impressions),
		'clicks_28d': int(clicks),
		'sessions_28d': int(sessions),
		'severity_weight': round(severity, 3),
		'index_risk': index_risk,
		'http_risk': http_risk,
		'rationale': 'traffic + severity + index/HTTP risk',
	}


def _impact_label(score: float) -> str:
	if score >= 0.7:
		return 'high'
	if score >= 0.4:
		return 'medium'
	return 'low'


def impact_sort_key(impact: dict[str, object]) -> float:
	return float(impact.get('score') or 0)
