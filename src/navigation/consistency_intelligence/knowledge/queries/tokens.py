"""Token query handlers."""
from __future__ import annotations

from collections import defaultdict

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph, TokenNode

from ..envelope import KnowledgeQuery, KnowledgeResponse, stub_response


def _all_tokens(graph: ProjectDesignGraph) -> list[TokenNode]:
	return [
		*graph.foundations.color_tokens,
		*graph.foundations.shadow_tokens,
		*graph.foundations.motion_tokens,
	]


def _used_token_paths(graph: ProjectDesignGraph) -> set[str]:
	used: set[str] = set()
	for edge in graph.relationships:
		if edge.kind == 'uses_token':
			used.add(edge.target)
	return used


def handle_tokens_declared(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	tokens = [t for t in _all_tokens(graph) if t.provenance in ('declared', 'merged')]
	if not tokens:
		declared = [t for t in _all_tokens(graph)]
		if not declared:
			return stub_response(graph, query, message='No tokens in graph — run Discovery Pipeline.')
		tokens = declared
	return KnowledgeResponse(
		query=query,
		answer={'status': 'ok', 'tokens': [t.to_dict() for t in tokens], 'count': len(tokens)},
		confidence=1.0,
		graph_version=graph.meta.graph_version,
	)


def handle_tokens_used(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	used_paths = _used_token_paths(graph)
	tokens = [t for t in _all_tokens(graph) if t.path_str in used_paths]
	edges = [r.to_dict() for r in graph.relationships if r.kind == 'uses_token']
	if not tokens and not edges:
		return stub_response(graph, query, message='No token usage edges in graph.')
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'tokens': [t.to_dict() for t in tokens],
			'usage_edges': edges,
			'count': len(tokens),
		},
		graph_version=graph.meta.graph_version,
	)


def handle_tokens_unused(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	declared = [t for t in _all_tokens(graph) if t.provenance in ('declared', 'merged')]
	if not declared:
		declared = _all_tokens(graph)
	used = _used_token_paths(graph)
	unused = [t for t in declared if t.path_str not in used]
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'unused_tokens': [t.to_dict() for t in unused],
			'count': len(unused),
			'declared_count': len(declared),
			'used_count': len(used),
		},
		confidence=1.0 if declared else 0.0,
		graph_version=graph.meta.graph_version,
		degraded=[] if declared else ['no_declared_tokens'],
	)


def _normalize_value(value: str | None) -> str:
	if value is None:
		return ''
	v = str(value).strip().lower().replace(' ', '')
	if v.startswith('#') and len(v) == 4:
		return '#' + ''.join(c * 2 for c in v[1:])
	return v


def handle_tokens_fragmentation(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	buckets: dict[str, list[TokenNode]] = defaultdict(list)
	for token in _all_tokens(graph):
		key = _normalize_value(str(token.resolved_value or token.value or ''))
		if not key:
			continue
		buckets[key].append(token)

	fragments = []
	for value, tokens in buckets.items():
		if len(tokens) < 2:
			continue
		paths = [t.path_str for t in tokens]
		if len(set(paths)) < 2:
			continue
		fragments.append({
			'normalized_value': value,
			'token_paths': paths,
			'count': len(tokens),
			'provenances': list({t.provenance for t in tokens}),
		})

	fragments.sort(key=lambda x: x['count'], reverse=True)
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'fragment_groups': fragments,
			'fragmentation_count': len(fragments),
		},
		confidence=1.0 if fragments else 0.5,
		graph_version=graph.meta.graph_version,
		degraded=[] if _all_tokens(graph) else ['no_tokens_in_graph'],
	)


TOKEN_HANDLERS = {
	'tokens.declared': handle_tokens_declared,
	'tokens.used': handle_tokens_used,
	'tokens.unused': handle_tokens_unused,
	'tokens.fragmentation': handle_tokens_fragmentation,
}
