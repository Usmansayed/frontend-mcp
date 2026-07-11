"""Shared query helpers."""
from __future__ import annotations

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph

from ..envelope import EvidenceRef, ExceptionRef, KnowledgeQuery, KnowledgeResponse, StandardRef, stub_response


def graph_meta(graph: ProjectDesignGraph, query: KnowledgeQuery) -> dict:
	return {
		'project_id': graph.meta.project_id,
		'graph_version': graph.meta.graph_version,
	}


def standards_from_graph(graph: ProjectDesignGraph) -> list[StandardRef]:
	out: list[StandardRef] = []
	for s in graph.foundations.standards:
		out.append(StandardRef.from_standard_node(s))
	for comp in graph.components.values():
		for s in comp.standards:
			out.append(StandardRef.from_standard_node(s))
	return out


def exceptions_from_graph(graph: ProjectDesignGraph, *, standard_id: str | None = None) -> list[ExceptionRef]:
	out: list[ExceptionRef] = []
	for ex in graph.exceptions:
		if standard_id and ex.standard_id != standard_id:
			continue
		out.append(
			ExceptionRef(
				standard_id=ex.standard_id,
				element_pattern=ex.element_pattern,
				actual_value=ex.actual_value,
				rationale=ex.rationale,
			)
		)
	return out


def group_deviations(deviations: list[dict]) -> list[dict]:
	groups: dict[tuple[str, str], dict] = {}
	for dev in deviations:
		std_id = str(dev.get('standard_id', ''))
		prop = str(dev.get('property', ''))
		key = (std_id, prop)
		entry = groups.get(key)
		if entry is None:
			entry = {
				'standard_id': std_id,
				'property': prop,
				'count': 0,
				'expected': dev.get('expected'),
				'examples': [],
			}
			groups[key] = entry
		entry['count'] += 1
		if len(entry['examples']) < 8:
			entry['examples'].append({
				'actual': dev.get('actual'),
				'confidence': dev.get('confidence'),
			})
	return list(groups.values())


def stub_handler(message: str | None = None):
	def _handler(graph: ProjectDesignGraph, query: KnowledgeQuery) -> KnowledgeResponse:
		return stub_response(graph, query, message=message)

	return _handler
