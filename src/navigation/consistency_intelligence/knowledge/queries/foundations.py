"""Foundation query handlers (Phase 1 stubs)."""
from __future__ import annotations

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph

from ..envelope import KnowledgeQuery, KnowledgeResponse, stub_response
from ._helpers import standards_from_graph, stub_handler


def handle_standard_for_context(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	context = str(query.params.get('context', ''))
	prop = query.params.get('property')
	property_name = str(prop) if prop else None
	if not context:
		resp = stub_response(graph, query, message='`context` param required.')
		resp.degraded.append('missing_param:context')
		return resp

	matches = graph.standards_for_context(context, property_name=property_name)
	if not matches:
		return stub_response(
			graph,
			query,
			message=f'No standards in graph for context `{context}` (Discovery Phase 2).',
		)

	from ..envelope import StandardRef

	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'context': context,
			'property': property_name,
			'count': len(matches),
		},
		standards=[StandardRef.from_standard_node(s) for s in matches],
		confidence=max(s.confidence for s in matches),
		graph_version=graph.meta.graph_version,
		degraded=[] if matches[0].support_count else ['standard_low_support'],
	)


def handle_typography_scale(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	if graph.foundations.typography_scale:
		scales = [s.to_dict() for s in graph.foundations.typography_scale]
		return KnowledgeResponse(
			query=query,
			answer={'status': 'ok', 'scales': scales},
			confidence=max(s.confidence for s in graph.foundations.typography_scale),
			graph_version=graph.meta.graph_version,
		)
	return stub_response(graph, query, message='Typography scale empty — run Discovery Pipeline (Phase 2).')


def handle_spacing_system(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	if graph.foundations.spacing_scale:
		scales = [s.to_dict() for s in graph.foundations.spacing_scale]
		return KnowledgeResponse(
			query=query,
			answer={'status': 'ok', 'scales': scales},
			confidence=max(s.confidence for s in graph.foundations.spacing_scale),
			graph_version=graph.meta.graph_version,
		)
	return stub_response(graph, query, message='Spacing scale empty — run Discovery Pipeline (Phase 2).')


def handle_radius_scale(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	if graph.foundations.radius_scale:
		scales = [s.to_dict() for s in graph.foundations.radius_scale]
		return KnowledgeResponse(
			query=query,
			answer={'status': 'ok', 'scales': scales},
			confidence=max(s.confidence for s in graph.foundations.radius_scale),
			graph_version=graph.meta.graph_version,
		)
	return stub_response(graph, query, message='Radius scale empty — run Discovery Pipeline (Phase 2).')


def handle_color_palette(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	if graph.foundations.color_tokens:
		tokens = [t.to_dict() for t in graph.foundations.color_tokens]
		return KnowledgeResponse(
			query=query,
			answer={'status': 'ok', 'tokens': tokens, 'count': len(tokens)},
			confidence=1.0,
			graph_version=graph.meta.graph_version,
		)
	return stub_response(graph, query, message='Color tokens empty — run Discovery Pipeline (Phase 2).')


FOUNDATION_HANDLERS = {
	'standard.for_context': handle_standard_for_context,
	'typography.scale': handle_typography_scale,
	'spacing.system': handle_spacing_system,
	'radius.scale': handle_radius_scale,
	'color.palette': handle_color_palette,
}
