"""Recommendation and correlation deduplication (Sprint 2)."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.models import SeoRecommendation

_FIX_FAMILY: dict[str, str] = {
	'indexing_rendering_correlation': 'indexing_rendering',
	'cwv_rendering_correlation': 'cwv_rendering',
	'ctr_cwv_correlation': 'ctr_cwv',
	'technical_index_correlation': 'technical_index',
	'broken_pages_with_search_visibility': 'broken_page',
	'traffic_query_landing_alignment': 'traffic_alignment',
	'opportunity_weak_metadata': 'metadata',
	'opportunity_internal_links': 'internal_links',
	'opportunity_indexing': 'indexing',
	'opportunity_cwv_quick_win': 'cwv',
	'dev_practice_metadata': 'metadata',
	'dev_practice_schema': 'schema',
	'dev_practice_accessibility_cwv': 'cwv_a11y',
	'dev_practice_rendering': 'rendering',
	'dev_practice_internal_links': 'internal_links',
	'dev_practice_semantic_html': 'semantic_html',
}


def dedupe_correlations(correlations: list[dict[str, Any]]) -> list[dict[str, Any]]:
	seen: set[str] = set()
	out: list[dict[str, Any]] = []
	for corr in correlations:
		key = _correlation_key(corr)
		if key in seen:
			continue
		seen.add(key)
		out.append(corr)
	return out


def dedupe_reasoning_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
	seen: set[str] = set()
	out: list[dict[str, Any]] = []
	for unit in units:
		key = '|'.join([
			normalize_page_url(str(unit.get('page_url') or '')),
			str(unit.get('correlation_id') or unit.get('kind') or ''),
		])
		if key in seen:
			continue
		seen.add(key)
		out.append(unit)
	return out


def dedupe_recommendations(recommendations: list[SeoRecommendation]) -> list[SeoRecommendation]:
	"""Merge recommendations targeting same page + fix family."""
	buckets: dict[str, SeoRecommendation] = {}
	order: list[str] = []

	for rec in recommendations:
		page = normalize_page_url(str((rec.metadata or {}).get('page_url') or ''))
		family = _fix_family(rec.recommendation_id, rec.category)
		key = f'{page}|{family}'
		if key not in buckets:
			buckets[key] = rec
			order.append(key)
			continue
		existing = buckets[key]
		merged_ids = list(dict.fromkeys(existing.evidence_ids + rec.evidence_ids))
		existing.evidence_ids = merged_ids
		if rec.confidence > existing.confidence:
			existing.confidence = rec.confidence
		impact_a = float((existing.metadata or {}).get('impact', {}).get('score', 0))
		impact_b = float((rec.metadata or {}).get('impact', {}).get('score', 0))
		if impact_b > impact_a:
			existing.metadata = {**(existing.metadata or {}), 'impact': (rec.metadata or {}).get('impact')}

	return [buckets[k] for k in order]


def _correlation_key(corr: dict[str, Any]) -> str:
	page = normalize_page_url(str(corr.get('page_url') or ''))
	analysis_id = str(corr.get('analysis_id') or '')
	family = _FIX_FAMILY.get(analysis_id, analysis_id)
	if analysis_id.startswith('opportunity_low_ctr'):
		family = 'low_ctr'
	elif analysis_id.startswith('opportunity_striking_distance'):
		family = 'striking_distance'
	elif analysis_id.startswith('opportunity_query_cwv'):
		family = 'query_cwv'
	return f'{page}|{family}'


def _fix_family(rec_id: str, category: str) -> str:
	if rec_id in _FIX_FAMILY:
		return _FIX_FAMILY[rec_id]
	if rec_id.startswith('rec_'):
		return category or 'evidence'
	for prefix, family in _FIX_FAMILY.items():
		if rec_id.startswith(prefix):
			return family
	if rec_id.startswith('opportunity_low_ctr'):
		return 'low_ctr'
	if rec_id.startswith('opportunity_striking_distance'):
		return 'striking_distance'
	return category or rec_id
