"""Page entity helpers for the SEO knowledge graph (ADR-027)."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url, page_url_for_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef


def group_evidence_by_page(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> dict[str, list[SeoEvidenceRef]]:
	pages: dict[str, list[SeoEvidenceRef]] = {}
	for item in evidence:
		page = page_url_for_evidence(item, base_url=base_url) or '__site__'
		pages.setdefault(page, []).append(item)
	return pages


def extract_page_metrics(items: list[SeoEvidenceRef]) -> dict[str, Any]:
	metrics: dict[str, Any] = {}
	for item in items:
		kind = item.kind.value
		if kind == 'core_web_vital' and item.metric_value is not None:
			key = str(item.metadata.get('auditId') or item.source_ref or item.title)
			if 'lcp' in key.lower() or 'largest-contentful-paint' in key.lower():
				metrics['lcp_ms'] = item.metric_value
			elif 'cls' in key.lower() or 'layout-shift' in key.lower():
				metrics['cls'] = item.metric_value
			elif item.metric_unit == 'ms':
				metrics.setdefault('cwv_ms', {})[key] = item.metric_value
		if kind == 'index_status':
			metrics['index_verdict'] = item.metadata.get('verdict') or _verdict_from_summary(item.summary)
		if kind == 'technical_issue' and item.metric_unit == 'status_code':
			metrics['http_status'] = int(item.metric_value or 0)
		if kind == 'search_query':
			metrics.setdefault('queries', []).append({
				'query': item.title,
				'impressions': item.metadata.get('impressions'),
				'ctr': item.metadata.get('ctr'),
				'position': item.metric_value or item.metadata.get('position'),
				'evidence_id': item.evidence_id,
			})
		if kind == 'traffic_metric':
			metrics.setdefault('sessions', 0.0)
			metrics['sessions'] = max(float(metrics['sessions']), float(item.metric_value or 0))
	return metrics


def page_entity_from_evidence(
	page_key: str,
	items: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> dict[str, Any]:
	url = '' if page_key == '__site__' else page_key
	return {
		'url': url,
		'page_key': page_key,
		'evidence_ids': [e.evidence_id for e in items],
		'evidence': [e.to_dict() for e in items],
		'metrics': extract_page_metrics(items),
		'providers': sorted({e.provider_id for e in items}),
	}


def merge_page_entity(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
	evidence_ids = list(dict.fromkeys(
		list(existing.get('evidence_ids') or []) + list(incoming.get('evidence_ids') or [])
	))
	return {
		'url': incoming.get('url') or existing.get('url') or '',
		'page_key': incoming.get('page_key') or existing.get('page_key') or '',
		'evidence_ids': evidence_ids,
		'providers': sorted(set(existing.get('providers') or []) | set(incoming.get('providers') or [])),
		'updated_at': incoming.get('updated_at') or existing.get('updated_at'),
	}


def _verdict_from_summary(summary: str) -> str:
	upper = summary.upper()
	for token in ('FAIL', 'PASS', 'PARTIAL', 'NEUTRAL'):
		if token in upper:
			return token
	return 'UNKNOWN'
