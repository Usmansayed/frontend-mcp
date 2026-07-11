"""Graph-level query handlers."""
from __future__ import annotations

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph
from navigation.consistency_intelligence.graph.persistence import graph_summary_stats

from ..envelope import ExceptionRef, KnowledgeQuery, KnowledgeResponse, stub_response
from ._helpers import exceptions_from_graph, standards_from_graph


def handle_graph_summary(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	stats = graph_summary_stats(graph)
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'stats': stats,
			'notes': graph.meta.notes,
			'learned_at': graph.meta.learned_at,
			'snapshot_count': graph.meta.snapshot_count,
		},
		standards=standards_from_graph(graph),
		exceptions=exceptions_from_graph(graph),
		confidence=graph.confidence.overall,
		degraded=['graph_empty'] if stats['standard_count'] == 0 and stats['component_count'] == 0 else [],
		graph_version=graph.meta.graph_version,
		meta={'project_id': graph.meta.project_id},
	)


def handle_graph_diff(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	other_version = str(query.params.get('other_version', '') or query.params.get('version', ''))
	if not other_version:
		return stub_response(graph, query, message='`other_version` param required for graph.diff.')

	from pathlib import Path

	from navigation.consistency_intelligence.graph.persistence import GraphStore

	repo_root = graph.meta.repo_root or str(query.params.get('repo_root', ''))
	store = GraphStore(storage_root=Path(repo_root) if repo_root else None)
	other = store.load_version(graph.meta.project_id, other_version)
	if other is None:
		versions = store.list_versions(graph.meta.project_id)
		return stub_response(
			graph,
			query,
			message=f'Version `{other_version}` not found. Available: {versions[-5:]}',
		)

	cur_stats = graph_summary_stats(graph)
	other_stats = graph_summary_stats(other)
	cur_comps = set(graph.components.keys())
	other_comps = set(other.components.keys())

	stats_delta = {}
	for k, v in cur_stats.items():
		ov = other_stats.get(k, 0)
		if isinstance(v, (int, float)) and isinstance(ov, (int, float)):
			stats_delta[k] = v - ov
		elif v != ov:
			stats_delta[k] = {'from': ov, 'to': v}

	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'from_version': other.meta.graph_version,
			'to_version': graph.meta.graph_version,
			'stats_delta': stats_delta,
			'components_added': sorted(cur_comps - other_comps)[:50],
			'components_removed': sorted(other_comps - cur_comps)[:50],
			'snapshot_count_delta': graph.meta.snapshot_count - other.meta.snapshot_count,
		},
		confidence=1.0,
		graph_version=graph.meta.graph_version,
		meta={'available_versions': store.list_versions(graph.meta.project_id)[-10:]},
	)


def handle_exceptions_for(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	standard_id = str(query.params.get('standard_id', ''))
	exc = exceptions_from_graph(graph, standard_id=standard_id or None)
	if not exc and standard_id:
		return stub_response(graph, query, message=f'No exceptions for standard `{standard_id}`.')
	return KnowledgeResponse(
		query=query,
		answer={'status': 'ok', 'count': len(exc), 'standard_id': standard_id or None},
		exceptions=exc,
		graph_version=graph.meta.graph_version,
		degraded=['knowledge_query_stub_phase1'] if not exc else [],
	)


def handle_exceptions_list(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	exc = exceptions_from_graph(graph)
	return KnowledgeResponse(
		query=query,
		answer={'status': 'ok', 'count': len(exc)},
		exceptions=exc,
		graph_version=graph.meta.graph_version,
	)


GRAPH_HANDLERS = {
	'graph.summary': handle_graph_summary,
	'graph.diff': handle_graph_diff,
	'exceptions.for': handle_exceptions_for,
	'exceptions.list': handle_exceptions_list,
}
