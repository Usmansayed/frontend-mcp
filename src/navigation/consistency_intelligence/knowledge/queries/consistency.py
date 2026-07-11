"""Consistency query handlers — graph-backed assessment (Phase 3)."""
from __future__ import annotations

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph, StandardNode

from ..envelope import (
	Alternative,
	EvidenceRef,
	KnowledgeQuery,
	KnowledgeResponse,
	Recommendation,
	StandardRef,
	stub_response,
)
from ._helpers import exceptions_from_graph, group_deviations


def _infer_context(selector: str, params: dict) -> str:
	if params.get('context'):
		return str(params['context']).lower()
	token = selector.split('.')[0].split('#')[-1].split()[-1].strip()
	return token.lower() if token else 'element'


def _properties_for(params: dict) -> list[str]:
	raw = params.get('properties') or params.get('property')
	if raw is None:
		return []
	if isinstance(raw, str):
		return [raw]
	return [str(p) for p in raw]


def _actual_values(params: dict) -> dict[str, str]:
	raw = params.get('actual') or params.get('actual_values') or {}
	return {str(k): str(v) for k, v in raw.items()}


def _value_matches(actual: str, expected: list[str]) -> bool:
	actual_norm = actual.strip().lower()
	for exp in expected:
		if actual_norm == exp.strip().lower():
			return True
	return False


def _find_matching_exception(graph: ProjectDesignGraph, standard_id: str, selector: str, actual: str):
	for ex in graph.exceptions:
		if ex.standard_id != standard_id:
			continue
		if ex.element_pattern in selector or selector.endswith(ex.element_pattern):
			if ex.actual_value == actual:
				return ex
	return None


def _standards_to_assess(graph: ProjectDesignGraph, context: str, properties: list[str]) -> list[StandardNode]:
	standards = graph.standards_for_context(context)
	if properties:
		prop_set = set(properties)
		standards = [s for s in standards if s.property in prop_set]
	return standards


def _assess_standards(
	graph: ProjectDesignGraph,
	*,
	selector: str,
	context: str,
	properties: list[str],
	actual_values: dict[str, str],
) -> tuple[bool, list[dict], list[StandardNode], list[EvidenceRef]]:
	deviations: list[dict] = []
	matched: list[StandardNode] = []
	evidence: list[EvidenceRef] = []

	for std in _standards_to_assess(graph, context, properties):
		prop = std.property
		if prop not in actual_values:
			continue
		actual = actual_values[prop]
		matched.append(std)
		evidence.append(
			EvidenceRef(
				kind='observation',
				selector=selector or None,
				property_name=prop,
				value=actual,
			)
		)
		if _value_matches(actual, std.expected_values):
			continue
		if _find_matching_exception(graph, std.id, selector, actual):
			continue
		deviations.append({
			'property': prop,
			'actual': actual,
			'expected': list(std.expected_values),
			'standard_id': std.id,
			'confidence': std.confidence,
		})

	consistent = len(deviations) == 0 and bool(matched or not actual_values)
	return consistent, deviations, matched, evidence


def handle_consistency_assess(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	selector = str(query.params.get('selector', ''))
	context = _infer_context(selector, query.params)
	properties = _properties_for(query.params)
	actual_values = _actual_values(query.params)

	if not actual_values and not properties:
		return stub_response(
			graph,
			query,
			message='`actual`/`actual_values` or `properties` required for consistency.assess.',
		)

	consistent, deviations, matched, evidence = _assess_standards(
		graph,
		selector=selector,
		context=context,
		properties=properties,
		actual_values=actual_values,
	)

	if not matched and actual_values:
		return stub_response(
			graph,
			query,
			message=f'No standards in graph for context `{context}` (run Discovery Pipeline first).',
		)

	confidence = min((s.confidence for s in matched), default=0.0) if matched else 0.0
	grouped = group_deviations(deviations)
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'consistent': consistent,
			'context': context,
			'selector': selector,
			'deviations': deviations,
			'deviation_count': len(deviations),
			'grouped_deviations': grouped,
		},
		evidence=evidence,
		standards=[StandardRef.from_standard_node(s) for s in matched],
		confidence=confidence,
		exceptions=exceptions_from_graph(graph),
		graph_version=graph.meta.graph_version,
		degraded=[] if matched else ['no_matching_standards'],
	)


def handle_consistency_explain(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	selector = str(query.params.get('selector', ''))
	context = _infer_context(selector, query.params)
	properties = _properties_for(query.params)
	actual_values = _actual_values(query.params)

	if not actual_values:
		return stub_response(graph, query, message='`actual`/`actual_values` required for consistency.explain.')

	consistent, deviations, matched, evidence = _assess_standards(
		graph,
		selector=selector,
		context=context,
		properties=properties,
		actual_values=actual_values,
	)

	alternatives: list[Alternative] = []
	recommendation: Recommendation | None = None

	if deviations:
		primary = deviations[0]
		std = graph.find_standard(primary['standard_id'])
		if std:
			for val, weight in sorted(std.distribution.items(), key=lambda x: x[1], reverse=True)[1:4]:
				alternatives.append(
					Alternative(
						value=val,
						confidence=weight,
						context=std.context,
						note='From project distribution',
					)
				)
			top = std.expected_values[0] if std.expected_values else ''
			suggested = {d['property']: top for d in deviations}
			recommendation = Recommendation(
				action='align_to_standard',
				detail=f'Align {selector or context} to project {context} norms',
				suggested_values=suggested,
				confidence=std.confidence,
				rationale=f'{std.support_count} observations support {top} for {std.property}',
			)

	confidence = max((s.confidence for s in matched), default=0.0)

	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'consistent': consistent,
			'context': context,
			'selector': selector,
			'deviations': deviations,
		},
		evidence=evidence,
		standards=[StandardRef.from_standard_node(s) for s in matched],
		confidence=confidence,
		exceptions=exceptions_from_graph(graph, standard_id=deviations[0]['standard_id'] if deviations else None),
		alternatives=alternatives,
		recommendation=recommendation,
		graph_version=graph.meta.graph_version,
	)


def handle_fix_recommend(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	standard_id = str(query.params.get('standard_id', ''))
	selector = str(query.params.get('selector', ''))
	actual_values = _actual_values(query.params)

	if not standard_id:
		return stub_response(graph, query, message='`standard_id` required for fix.recommend.')

	std = graph.find_standard(standard_id)
	if std is None:
		return stub_response(graph, query, message=f'Standard `{standard_id}` not found in graph.')

	expected = std.expected_values[0] if std.expected_values else ''
	suggested = {std.property: expected}

	explain = handle_consistency_explain(
		graph,
		KnowledgeQuery(
			query_id='consistency.explain',
			params={
				'selector': selector,
				'context': std.context,
				'properties': [std.property],
				'actual': actual_values or {std.property: query.params.get('actual', '')},
			},
		),
	)

	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'ok',
			'standard_id': standard_id,
			'suggested_values': suggested,
		},
		standards=[StandardRef.from_standard_node(std)],
		confidence=std.confidence,
		recommendation=explain.recommendation or Recommendation(
			action='align_to_standard',
			detail=f'Apply project standard for {std.property}',
			suggested_values=suggested,
			confidence=std.confidence,
			rationale=f'Canonical value from graph standard {standard_id}',
		),
		alternatives=explain.alternatives,
		graph_version=graph.meta.graph_version,
	)


def handle_confidence_for(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
	standard_id = str(query.params.get('standard_id', ''))
	if standard_id:
		std = graph.find_standard(standard_id)
		if std:
			return KnowledgeResponse(
				query=query,
				answer={'status': 'ok', 'standard_id': standard_id, 'confidence': std.confidence},
				confidence=std.confidence,
				graph_version=graph.meta.graph_version,
			)
	return stub_response(graph, query, message=f'Standard `{standard_id}` not found in graph.')


CONSISTENCY_HANDLERS = {
	'consistency.explain': handle_consistency_explain,
	'consistency.assess': handle_consistency_assess,
	'fix.recommend': handle_fix_recommend,
	'confidence.for': handle_confidence_for,
}
