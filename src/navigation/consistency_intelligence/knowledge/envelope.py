"""Knowledge API response envelope — shared across all queries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeQuery:
	query_id: str
	params: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {'query_id': self.query_id, 'params': dict(self.params)}


@dataclass(slots=True)
class EvidenceRef:
	kind: str
	selector: str | None = None
	property_name: str | None = None
	value: str | None = None
	scan_id: str | None = None
	file_path: str | None = None
	line: int | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'kind': self.kind,
			'selector': self.selector,
			'property': self.property_name,
			'value': self.value,
			'scan_id': self.scan_id,
			'file_path': self.file_path,
			'line': self.line,
		}


@dataclass(slots=True)
class StandardRef:
	id: str
	category: str
	context: str
	property_name: str
	expected_values: list[str] = field(default_factory=list)
	confidence: float = 0.0
	support_count: int = 0
	provenance: str = 'learned'

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'category': self.category,
			'context': self.context,
			'property': self.property_name,
			'expected_values': list(self.expected_values),
			'confidence': self.confidence,
			'support_count': self.support_count,
			'provenance': self.provenance,
		}

	@classmethod
	def from_standard_node(cls, node: Any) -> StandardRef:
		return cls(
			id=node.id,
			category=node.category,
			context=node.context,
			property_name=node.property,
			expected_values=list(node.expected_values),
			confidence=node.confidence,
			support_count=node.support_count,
			provenance=node.provenance,
		)


@dataclass(slots=True)
class ExceptionRef:
	standard_id: str
	element_pattern: str
	actual_value: str
	rationale: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'standard_id': self.standard_id,
			'element_pattern': self.element_pattern,
			'actual_value': self.actual_value,
			'rationale': self.rationale,
		}


@dataclass(slots=True)
class Alternative:
	value: str
	confidence: float
	context: str
	note: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'value': self.value,
			'confidence': self.confidence,
			'context': self.context,
			'note': self.note,
		}


@dataclass(slots=True)
class Recommendation:
	action: str
	detail: str
	suggested_values: dict[str, str] = field(default_factory=dict)
	confidence: float = 0.0
	rationale: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'action': self.action,
			'detail': self.detail,
			'suggested_values': dict(self.suggested_values),
			'confidence': self.confidence,
			'rationale': self.rationale,
		}


@dataclass(slots=True)
class KnowledgeResponse:
	"""Universal wrapper — all Knowledge API queries return this shape."""

	query: KnowledgeQuery
	answer: dict[str, Any] = field(default_factory=dict)
	evidence: list[EvidenceRef] = field(default_factory=list)
	standards: list[StandardRef] = field(default_factory=list)
	confidence: float = 0.0
	exceptions: list[ExceptionRef] = field(default_factory=list)
	alternatives: list[Alternative] = field(default_factory=list)
	recommendation: Recommendation | None = None
	degraded: list[str] = field(default_factory=list)
	graph_version: str = ''
	meta: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query.to_dict(),
			'answer': dict(self.answer),
			'evidence': [e.to_dict() for e in self.evidence],
			'standards': [s.to_dict() for s in self.standards],
			'confidence': self.confidence,
			'exceptions': [e.to_dict() for e in self.exceptions],
			'alternatives': [a.to_dict() for a in self.alternatives],
			'recommendation': self.recommendation.to_dict() if self.recommendation else None,
			'degraded': list(self.degraded),
			'graph_version': self.graph_version,
			'meta': dict(self.meta),
		}

	def summary_text(self) -> str:
		"""Human-readable summary for MCP envelopes."""
		status = self.answer.get('status', 'ok')
		if status == 'stub':
			return str(self.answer.get('message', 'Knowledge query stub (Phase 1).'))
		if self.query.query_id == 'graph.summary':
			stats = self.answer.get('stats') or {}
			return (
				f"Project design graph {self.graph_version}: "
				f"{stats.get('standard_count', 0)} standards, "
				f"{stats.get('component_count', 0)} components."
			)
		return f"Knowledge query {self.query.query_id} completed (confidence={self.confidence:.2f})."


def stub_response(
	graph: Any,
	query: KnowledgeQuery,
	*,
	message: str | None = None,
) -> KnowledgeResponse:
	"""Phase 1 stub — graph loaded but discovery not implemented."""
	return KnowledgeResponse(
		query=query,
		answer={
			'status': 'stub',
			'message': message or f'Query `{query.query_id}` is registered; Discovery Pipeline populates graph in Phase 2.',
			'graph_populated': _graph_has_data(graph),
		},
		confidence=0.0,
		degraded=['knowledge_query_stub_phase1', 'discovery_pipeline_phase2'],
		graph_version=graph.meta.graph_version,
		meta={'phase': 1},
	)


def _graph_has_data(graph: Any) -> bool:
	return bool(
		graph.foundations.standards
		or graph.components
		or graph.foundations.color_tokens
		or graph.foundations.spacing_scale
	)
