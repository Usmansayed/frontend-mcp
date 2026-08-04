"""Consistency query handlers — graph-backed assessment (Phase 3)."""
from __future__ import annotations

import re

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

# Observation CSS props → foundation contexts learned from snapshots.
_PROP_TO_FOUNDATION: dict[str, tuple[str, ...]] = {
	'font-size': ('typography',),
	'font-family': ('typography',),
	'font-weight': ('typography',),
	'line-height': ('typography',),
	'padding': ('spacing',),
	'margin': ('spacing',),
	'gap': ('spacing',),
	'color': ('color', 'colors', 'palette'),
	'background-color': ('color', 'colors', 'palette'),
	'border-radius': ('radius', 'spacing'),
}
_SPACING_STANDARD_PROPS = frozenset({'scale', 'base-unit', 'padding', 'gap', 'margin', 'spacing'})


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


def _normalize_css_value(value: str) -> str:
	text = value.strip().lower().replace(' ', '')
	m = re.fullmatch(r'(-?\d+(?:\.\d+)?)px', text)
	if m:
		num = float(m.group(1))
		if num.is_integer():
			return f'{int(num)}px'
		return f'{num}px'
	return text


def _value_matches(actual: str, expected: list[str]) -> bool:
	actual_norm = _normalize_css_value(actual)
	expected_norms = {_normalize_css_value(exp) for exp in expected}
	if actual_norm in expected_norms:
		return True
	# Multi-token shorthand (padding/margin): any side in the learned scale.
	for part in re.findall(r'-?\d+(?:\.\d+)?px', actual.lower()):
		if _normalize_css_value(part) in expected_norms:
			return True
	return False


def _find_matching_exception(graph: ProjectDesignGraph, standard_id: str, selector: str, actual: str):
	for ex in graph.exceptions:
		if ex.standard_id != standard_id:
			continue
		if ex.element_pattern in selector or selector.endswith(ex.element_pattern):
			if _normalize_css_value(ex.actual_value) == _normalize_css_value(actual):
				return ex
	return None


def _standards_to_assess(
	graph: ProjectDesignGraph,
	context: str,
	properties: list[str],
	actual_values: dict[str, str] | None = None,
) -> list[StandardNode]:
	"""Match by element context, then broaden via CSS property → foundation context."""
	seen: set[str] = set()
	out: list[StandardNode] = []

	def _add(std: StandardNode) -> None:
		if std.id in seen:
			return
		seen.add(std.id)
		out.append(std)

	for std in graph.standards_for_context(context):
		_add(std)

	props = list(properties) if properties else list((actual_values or {}).keys())
	for prop in props:
		for alias in _PROP_TO_FOUNDATION.get(prop, ()):
			for std in graph.standards_for_context(alias):
				_add(std)
		for std in list(graph.foundations.standards):
			if std.property == prop:
				_add(std)
			elif prop in ('padding', 'gap', 'margin') and std.property in _SPACING_STANDARD_PROPS:
				_add(std)
			elif prop in ('font-size', 'font-family') and std.property in (
				'font-size',
				'font-family',
				'scale',
			):
				_add(std)
	return out


def _actual_for_standard(std: StandardNode, actual_values: dict[str, str]) -> str | None:
	if std.property in actual_values:
		return actual_values[std.property]
	if std.property in _SPACING_STANDARD_PROPS:
		for key in ('padding', 'gap', 'margin'):
			if key in actual_values:
				return actual_values[key]
	if std.property in ('font-size', 'scale') and 'font-size' in actual_values:
		return actual_values['font-size']
	if std.property == 'font-family' and 'font-family' in actual_values:
		return actual_values['font-family']
	return None


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

	for std in _standards_to_assess(graph, context, properties, actual_values):
		actual = _actual_for_standard(std, actual_values)
		if actual is None:
			continue
		matched.append(std)
		evidence.append(
			EvidenceRef(
				kind='observation',
				selector=selector or None,
				property_name=std.property,
				value=actual,
			)
		)
		if _value_matches(actual, std.expected_values):
			continue
		if _find_matching_exception(graph, std.id, selector, actual):
			continue
		deviations.append({
			'property': std.property,
			'actual': actual,
			'expected': list(std.expected_values),
			'standard_id': std.id,
			'confidence': std.confidence,
		})

	consistent = len(deviations) == 0 and bool(matched)
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

	graph_has_standards = bool(graph.foundations.standards) or any(
		bool(c.standards) for c in graph.components.values()
	)

	if not matched and actual_values:
		# Populated graph but no overlap — skip observation; do NOT emit Phase-1 stub codes.
		if graph_has_standards:
			return KnowledgeResponse(
				query=query,
				answer={
					'status': 'ok',
					'consistent': True,
					'skipped': True,
					'context': context,
					'selector': selector,
					'deviations': [],
					'deviation_count': 0,
					'grouped_deviations': [],
					'message': (
						f'No overlapping standards for context `{context}` / '
						f'props {sorted(actual_values)}; observation skipped.'
					),
				},
				confidence=0.4,
				degraded=['observation_no_matching_standard'],
				graph_version=graph.meta.graph_version,
				meta={'skipped': True, 'graph_populated': True},
			)
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
