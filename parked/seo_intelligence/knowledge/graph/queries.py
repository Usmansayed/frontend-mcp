"""SEO graph query handlers — agent-facing read API."""
from __future__ import annotations

from typing import Any, Callable

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore

QueryHandler = Callable[[SeoKnowledgeGraphStore, dict[str, Any]], dict[str, Any]]

_ISSUE_KINDS = frozenset({
	'crawl_issue', 'technical_issue', 'rendering_issue', 'index_status',
	'core_web_vital', 'performance',
})


def list_graph_queries() -> list[dict[str, Any]]:
	return [
		{
			'query_id': 'graph.summary',
			'description': 'Graph counts, latest audit, website',
			'params': [],
		},
		{
			'query_id': 'page.issues',
			'description': 'All issues and evidence on a page URL',
			'params': ['page_url'],
		},
		{
			'query_id': 'audit.latest',
			'description': 'Latest audit snapshot metadata',
			'params': [],
		},
		{
			'query_id': 'audit.diff',
			'description': 'Evidence changes since previous audit',
			'params': ['audit_id'],
		},
		{
			'query_id': 'site.traffic_signals',
			'description': 'Hypotheses for traffic/index changes between audits',
			'params': [],
		},
		{
			'query_id': 'ai.readiness.summary',
			'description': 'Overall + per-dimension AI readiness scores from the latest audit',
			'params': [],
		},
		{
			'query_id': 'page.ai_readiness',
			'description': 'AI readiness signals for a specific page with cited upstream evidence',
			'params': ['page_url'],
		},
	]


def run_graph_query(
	store: SeoKnowledgeGraphStore,
	query_id: str,
	params: dict[str, Any] | None = None,
) -> dict[str, Any]:
	params = dict(params or {})
	handler = _HANDLERS.get(query_id)
	if handler is None:
		return {
			'ok': False,
			'query_id': query_id,
			'error': f'unknown_query_id:{query_id}',
			'available_queries': [q['query_id'] for q in list_graph_queries()],
		}
	result = handler(store, params)
	return {'ok': True, 'query_id': query_id, 'params': params, 'result': result}


def _handle_graph_summary(store: SeoKnowledgeGraphStore, _params: dict[str, Any]) -> dict[str, Any]:
	return store.summary()


def _handle_page_issues(store: SeoKnowledgeGraphStore, params: dict[str, Any]) -> dict[str, Any]:
	page_url = normalize_page_url(str(params.get('page_url') or ''))
	if not page_url:
		return {'error': 'page_url_required'}

	data = store.load()
	page_key = page_url
	page = (data.get('pages') or {}).get(page_key)
	evidence_bucket = data.get('evidence') or {}

	evidence_ids = list(page.get('evidence_ids') or []) if isinstance(page, dict) else []
	items = [evidence_bucket[eid] for eid in evidence_ids if eid in evidence_bucket]

	issues = [
		item for item in items
		if isinstance(item, dict) and str(item.get('kind') or '') in _ISSUE_KINDS
	]
	opportunities = list((data.get('opportunities') or {}).values())

	audit_id = store.latest_audit_id()
	reasoning_units = []
	if audit_id:
		snapshot = store.get_audit_snapshot(audit_id)
		if snapshot:
			ctx = snapshot.get('reasoning_context_v2') or {}
			reasoning_units = [
				u for u in (ctx.get('reasoning_units') or [])
				if isinstance(u, dict) and normalize_page_url(str(u.get('page_url') or '')) == page_url
			]

	return {
		'page_url': page_url,
		'page': page,
		'issue_count': len(issues),
		'issues': issues,
		'reasoning_units': reasoning_units,
		'recommendations': [
			r for r in (data.get('recommendations') or {}).values()
			if isinstance(r, dict)
			and normalize_page_url(str((r.get('metadata') or {}).get('page_url') or '')) == page_url
		],
		'opportunity_count': len(opportunities),
	}


def _handle_audit_latest(store: SeoKnowledgeGraphStore, _params: dict[str, Any]) -> dict[str, Any]:
	audit_id = store.latest_audit_id()
	if not audit_id:
		return {'audit_id': '', 'message': 'no_audits_yet'}
	snapshot = store.get_audit_snapshot(audit_id)
	if not snapshot:
		return {'audit_id': audit_id, 'message': 'snapshot_missing'}
	return {
		'audit_id': audit_id,
		'collected_at': snapshot.get('collected_at'),
		'mode': snapshot.get('mode'),
		'providers_queried': snapshot.get('providers_queried'),
		'evidence_count': len(snapshot.get('evidence_ids') or []),
		'recommendation_count': len(snapshot.get('recommendation_ids') or []),
		'reasoning_unit_count': len(
			(snapshot.get('reasoning_context_v2') or {}).get('reasoning_units') or []
		),
	}


def _handle_audit_diff(store: SeoKnowledgeGraphStore, params: dict[str, Any]) -> dict[str, Any]:
	audit_id = str(params.get('audit_id') or store.latest_audit_id())
	if not audit_id:
		return {'error': 'no_audit_id'}
	previous = store.previous_audit_id(audit_id)
	if not previous:
		return {
			'audit_id': audit_id,
			'message': 'no_previous_audit_for_diff',
		}
	diff = store.build_snapshot_diff(audit_id, previous)
	return diff or {'error': 'diff_unavailable'}


def _handle_traffic_signals(store: SeoKnowledgeGraphStore, _params: dict[str, Any]) -> dict[str, Any]:
	audit_id = store.latest_audit_id()
	if not audit_id:
		return {'hypotheses': [], 'message': 'no_audits_yet'}

	previous = store.previous_audit_id(audit_id)
	diff = store.build_snapshot_diff(audit_id, previous) if previous else None
	snapshot = store.get_audit_snapshot(audit_id)
	evidence = (snapshot or {}).get('evidence') or {}

	hypotheses: list[dict[str, Any]] = []

	if diff:
		degraded = diff.get('evidence_degraded') or []
		improved = diff.get('evidence_improved') or []
		if degraded:
			traffic_new = [
				eid for eid in degraded
				if str((evidence.get(eid) or {}).get('kind') or '') == 'traffic_metric'
			]
			index_new = [
				eid for eid in degraded
				if str((evidence.get(eid) or {}).get('kind') or '') == 'index_status'
			]
			if traffic_new:
				hypotheses.append({
					'kind': 'traffic_change',
					'title': 'New traffic signals detected',
					'summary': 'Traffic metrics appeared or worsened since last audit.',
					'evidence_ids': traffic_new[:5],
				})
			if index_new:
				hypotheses.append({
					'kind': 'indexing_regression',
					'title': 'New indexing issues',
					'summary': 'Index coverage degraded since last audit — check GSC and rendering.',
					'evidence_ids': index_new[:5],
				})
		if improved and not hypotheses:
			hypotheses.append({
				'kind': 'recovery',
				'title': 'Issues resolved since last audit',
				'summary': f'{len(improved)} evidence item(s) improved or cleared.',
				'evidence_ids': improved[:5],
			})

	traffic_items = [
		v for v in evidence.values()
		if isinstance(v, dict) and v.get('kind') == 'traffic_metric'
	]
	if traffic_items and not any(h['kind'] == 'traffic_change' for h in hypotheses):
		sessions = [float(t.get('metric_value') or 0) for t in traffic_items]
		max_sessions = max(sessions) if sessions else 0.0
		hypotheses.append({
			'kind': 'traffic_snapshot',
			'title': 'Current landing-page traffic',
			'summary': f'{len(traffic_items)} traffic metric(s); max sessions {max_sessions:.0f}.',
			'evidence_ids': [str(t.get('evidence_id')) for t in traffic_items[:5]],
		})

	ctx = (snapshot or {}).get('reasoning_context_v2') or {}
	site_correlations = ctx.get('site_correlations') or []
	for corr in site_correlations[:3]:
		if isinstance(corr, dict) and 'traffic' in str(corr.get('analysis_id') or '').lower():
			hypotheses.append({
				'kind': 'site_correlation',
				'title': str(corr.get('title') or ''),
				'summary': str(corr.get('summary') or ''),
				'evidence_ids': list(corr.get('evidence_ids') or [])[:5],
			})

	return {
		'audit_id': audit_id,
		'previous_audit_id': previous,
		'diff': diff,
		'hypotheses': hypotheses,
	}


def _handle_ai_readiness_summary(store: SeoKnowledgeGraphStore, _params: dict[str, Any]) -> dict[str, Any]:
	audit_id = store.latest_audit_id()
	if not audit_id:
		return {'audit_id': '', 'message': 'no_audits_yet'}
	snapshot = store.get_audit_snapshot(audit_id) or {}
	ctx = snapshot.get('reasoning_context_v2') or {}
	block = ctx.get('ai_readiness') or {}
	if not block:
		return {
			'audit_id': audit_id,
			'message': 'ai_readiness_not_computed_for_this_audit',
		}
	return {
		'audit_id': audit_id,
		'overall_score': block.get('overall_score'),
		'analyzers_run': block.get('analyzers_run'),
		'analyzers_skipped': block.get('analyzers_skipped'),
		'dimensions': block.get('dimensions'),
		'sources_documented_in': block.get('sources_documented_in'),
	}


def _handle_page_ai_readiness(store: SeoKnowledgeGraphStore, params: dict[str, Any]) -> dict[str, Any]:
	page_url = normalize_page_url(str(params.get('page_url') or ''))
	if not page_url:
		return {'error': 'page_url_required'}
	data = store.load()
	ai_signals = data.get('ai_signals') or {}
	matched = [
		item for item in ai_signals.values()
		if isinstance(item, dict)
		and normalize_page_url(str(item.get('page_url') or '')) == page_url
	]
	evidence_bucket = data.get('evidence') or {}
	cited: list[dict[str, Any]] = []
	seen: set[str] = set()
	for item in matched:
		for eid in (item.get('metadata') or {}).get('source_evidence_ids') or []:
			if eid in seen or eid not in evidence_bucket:
				continue
			seen.add(eid)
			cited.append(evidence_bucket[eid])
	return {
		'page_url': page_url,
		'ai_signal_count': len(matched),
		'ai_signals': matched,
		'source_evidence': cited,
	}


_HANDLERS: dict[str, QueryHandler] = {
	'graph.summary': _handle_graph_summary,
	'page.issues': _handle_page_issues,
	'audit.latest': _handle_audit_latest,
	'audit.diff': _handle_audit_diff,
	'site.traffic_signals': _handle_traffic_signals,
	'ai.readiness.summary': _handle_ai_readiness_summary,
	'page.ai_readiness': _handle_page_ai_readiness,
}
