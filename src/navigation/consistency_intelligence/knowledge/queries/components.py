"""Component query handlers."""
from __future__ import annotations

from navigation.consistency_intelligence.graph.model import ComponentNode, ProjectDesignGraph

from ..envelope import KnowledgeQuery, KnowledgeResponse, StandardRef, stub_response


def _get_component(graph: ProjectDesignGraph, name: str) -> ComponentNode | None:
	key = name.lower()
	return graph.components.get(name) or graph.components.get(key)


def _similarity_score(a: ComponentNode, b: ComponentNode) -> float:
	if a.name.lower() == b.name.lower():
		return 1.0
	score = 0.0
	variant_overlap = set(v.lower() for v in a.variants) & set(v.lower() for v in b.variants)
	if variant_overlap:
		score += 0.3 + 0.1 * len(variant_overlap)
	state_overlap = set(a.states) & set(b.states)
	if state_overlap:
		score += 0.1 * len(state_overlap)
	prop_a = {s.property for s in a.standards}
	prop_b = {s.property for s in b.standards}
	prop_overlap = prop_a & prop_b
	if prop_overlap:
		score += 0.2 + 0.05 * len(prop_overlap)
	if a.name.split('_')[0].lower() == b.name.split('_')[0].lower():
		score += 0.15
	return min(score, 0.99)


def handle_component_variants(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	component = str(query.params.get('component', ''))
	if not component:
		resp = stub_response(graph, query, message='`component` param required.')
		resp.degraded.append('missing_param:component')
		return resp
	comp = _get_component(graph, component)
	if comp is None:
		return stub_response(graph, query, message=f'Component `{component}` not in graph.')
	return KnowledgeResponse(
		query=query,
		answer={'status': 'ok', 'component': comp.name, 'variants': list(comp.variants)},
		standards=[StandardRef.from_standard_node(s) for s in comp.standards],
		confidence=comp.confidence,
		graph_version=graph.meta.graph_version,
	)


def handle_component_canonical(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	component = str(query.params.get('component', ''))
	comp = _get_component(graph, component) if component else None
	if comp is None:
		return stub_response(graph, query, message=f'Component `{component}` not in graph.')
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'component': comp.name,
			'canonical_variant': comp.canonical_variant or (comp.variants[0] if comp.variants else ''),
		},
		confidence=comp.confidence,
		graph_version=graph.meta.graph_version,
	)


def handle_component_similar(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	component = str(query.params.get('component', ''))
	reference = str(query.params.get('selector', '') or query.params.get('reference', ''))
	if not component:
		return stub_response(graph, query, message='`component` param required.')
	ref = _get_component(graph, component)
	if ref is None:
		return stub_response(graph, query, message=f'Component `{component}` not in graph.')

	scored: list[tuple[float, ComponentNode]] = []
	for comp in graph.components.values():
		if comp.name.lower() == ref.name.lower():
			continue
		score = _similarity_score(ref, comp)
		if score > 0.2:
			scored.append((score, comp))
	scored.sort(key=lambda x: x[0], reverse=True)
	top = scored[:8]

	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'reference': ref.name,
			'reference_selector': reference or None,
			'similar': [
				{'component': comp.name, 'score': round(score, 3), 'variants': list(comp.variants)}
				for score, comp in top
			],
		},
		confidence=top[0][0] if top else 0.0,
		graph_version=graph.meta.graph_version,
		degraded=[] if top else ['no_similar_components'],
	)


def handle_component_states(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	component = str(query.params.get('component', ''))
	comp = _get_component(graph, component) if component else None
	if comp is None:
		return stub_response(graph, query, message=f'Component `{component}` not in graph.')
	return KnowledgeResponse(
		query=query,
		answer={'status': 'ok', 'component': comp.name, 'states': list(comp.states)},
		confidence=comp.confidence,
		graph_version=graph.meta.graph_version,
	)


COMPONENT_HANDLERS = {
	'component.variants': handle_component_variants,
	'component.canonical': handle_component_canonical,
	'component.similar': handle_component_similar,
	'component.states': handle_component_states,
}
