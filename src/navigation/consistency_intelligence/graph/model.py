"""Project Design Graph — the single source of design-language truth."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .version import new_graph_version


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class GraphMeta:
	project_id: str
	graph_version: str = ''
	learned_at: str = ''
	snapshot_count: int = 0
	repo_root: str = ''
	notes: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'project_id': self.project_id,
			'graph_version': self.graph_version,
			'learned_at': self.learned_at,
			'snapshot_count': self.snapshot_count,
			'repo_root': self.repo_root,
			'notes': self.notes,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> GraphMeta:
		return cls(
			project_id=str(data.get('project_id', 'default')),
			graph_version=str(data.get('graph_version', '')),
			learned_at=str(data.get('learned_at', '')),
			snapshot_count=int(data.get('snapshot_count', 0)),
			repo_root=str(data.get('repo_root', '')),
			notes=str(data.get('notes', '')),
		)


@dataclass(slots=True)
class TokenNode:
	"""DTCG-compatible token node in the graph."""

	path: tuple[str, ...]
	dtcg_type: str | None = None
	value: Any = None
	resolved_value: Any = None
	layer: str = 'primitive'  # primitive | semantic | component
	source: str = ''
	provenance: str = 'declared'  # learned | declared | merged
	confidence: float = 1.0
	extensions: dict[str, Any] = field(default_factory=dict)

	@property
	def path_str(self) -> str:
		return '.'.join(self.path)

	def to_dict(self) -> dict[str, Any]:
		return {
			'path': list(self.path),
			'dtcg_type': self.dtcg_type,
			'value': self.value,
			'resolved_value': self.resolved_value,
			'layer': self.layer,
			'source': self.source,
			'provenance': self.provenance,
			'confidence': self.confidence,
			'extensions': dict(self.extensions),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> TokenNode:
		path = data.get('path') or []
		return cls(
			path=tuple(str(p) for p in path),
			dtcg_type=data.get('dtcg_type'),
			value=data.get('value'),
			resolved_value=data.get('resolved_value'),
			layer=str(data.get('layer', 'primitive')),
			source=str(data.get('source', '')),
			provenance=str(data.get('provenance', 'declared')),
			confidence=float(data.get('confidence', 1.0)),
			extensions=dict(data.get('extensions') or {}),
		)


@dataclass(slots=True)
class StandardNode:
	"""A learned or merged design standard (property norm for a context)."""

	id: str
	category: str
	context: str
	property: str
	expected_values: list[str] = field(default_factory=list)
	distribution: dict[str, float] = field(default_factory=dict)
	confidence: float = 0.0
	support_count: int = 0
	provenance: str = 'learned'
	evidence_sample: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'category': self.category,
			'context': self.context,
			'property': self.property,
			'expected_values': list(self.expected_values),
			'distribution': dict(self.distribution),
			'confidence': self.confidence,
			'support_count': self.support_count,
			'provenance': self.provenance,
			'evidence_sample': list(self.evidence_sample),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> StandardNode:
		return cls(
			id=str(data['id']),
			category=str(data.get('category', '')),
			context=str(data.get('context', '')),
			property=str(data.get('property', '')),
			expected_values=list(data.get('expected_values') or []),
			distribution={str(k): float(v) for k, v in (data.get('distribution') or {}).items()},
			confidence=float(data.get('confidence', 0.0)),
			support_count=int(data.get('support_count', 0)),
			provenance=str(data.get('provenance', 'learned')),
			evidence_sample=list(data.get('evidence_sample') or []),
		)


@dataclass(slots=True)
class ScaleCluster:
	"""Numeric scale cluster (spacing, typography, radius)."""

	name: str
	values: list[str] = field(default_factory=list)
	unit: str = 'px'
	confidence: float = 0.0
	support_count: int = 0

	def to_dict(self) -> dict[str, Any]:
		return {
			'name': self.name,
			'values': list(self.values),
			'unit': self.unit,
			'confidence': self.confidence,
			'support_count': self.support_count,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> ScaleCluster:
		return cls(
			name=str(data.get('name', '')),
			values=[str(v) for v in (data.get('values') or [])],
			unit=str(data.get('unit', 'px')),
			confidence=float(data.get('confidence', 0.0)),
			support_count=int(data.get('support_count', 0)),
		)


@dataclass(slots=True)
class FoundationsLayer:
	color_tokens: list[TokenNode] = field(default_factory=list)
	typography_scale: list[ScaleCluster] = field(default_factory=list)
	spacing_scale: list[ScaleCluster] = field(default_factory=list)
	radius_scale: list[ScaleCluster] = field(default_factory=list)
	shadow_tokens: list[TokenNode] = field(default_factory=list)
	motion_tokens: list[TokenNode] = field(default_factory=list)
	standards: list[StandardNode] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'color_tokens': [t.to_dict() for t in self.color_tokens],
			'typography_scale': [s.to_dict() for s in self.typography_scale],
			'spacing_scale': [s.to_dict() for s in self.spacing_scale],
			'radius_scale': [s.to_dict() for s in self.radius_scale],
			'shadow_tokens': [t.to_dict() for t in self.shadow_tokens],
			'motion_tokens': [t.to_dict() for t in self.motion_tokens],
			'standards': [s.to_dict() for s in self.standards],
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any] | None) -> FoundationsLayer:
		if not data:
			return cls()
		return cls(
			color_tokens=[TokenNode.from_dict(t) for t in data.get('color_tokens') or []],
			typography_scale=[ScaleCluster.from_dict(s) for s in data.get('typography_scale') or []],
			spacing_scale=[ScaleCluster.from_dict(s) for s in data.get('spacing_scale') or []],
			radius_scale=[ScaleCluster.from_dict(s) for s in data.get('radius_scale') or []],
			shadow_tokens=[TokenNode.from_dict(t) for t in data.get('shadow_tokens') or []],
			motion_tokens=[TokenNode.from_dict(t) for t in data.get('motion_tokens') or []],
			standards=[StandardNode.from_dict(s) for s in data.get('standards') or []],
		)


@dataclass(slots=True)
class ComponentNode:
	name: str
	variants: list[str] = field(default_factory=list)
	states: list[str] = field(default_factory=list)
	standards: list[StandardNode] = field(default_factory=list)
	support_count: int = 0
	confidence: float = 0.0
	canonical_variant: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'name': self.name,
			'variants': list(self.variants),
			'states': list(self.states),
			'standards': [s.to_dict() for s in self.standards],
			'support_count': self.support_count,
			'confidence': self.confidence,
			'canonical_variant': self.canonical_variant,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> ComponentNode:
		return cls(
			name=str(data.get('name', '')),
			variants=list(data.get('variants') or []),
			states=list(data.get('states') or []),
			standards=[StandardNode.from_dict(s) for s in data.get('standards') or []],
			support_count=int(data.get('support_count', 0)),
			confidence=float(data.get('confidence', 0.0)),
			canonical_variant=str(data.get('canonical_variant', '')),
		)


@dataclass(slots=True)
class PatternNode:
	name: str
	description: str = ''
	component_refs: list[str] = field(default_factory=list)
	confidence: float = 0.0
	support_count: int = 0

	def to_dict(self) -> dict[str, Any]:
		return {
			'name': self.name,
			'description': self.description,
			'component_refs': list(self.component_refs),
			'confidence': self.confidence,
			'support_count': self.support_count,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> PatternNode:
		return cls(
			name=str(data.get('name', '')),
			description=str(data.get('description', '')),
			component_refs=list(data.get('component_refs') or []),
			confidence=float(data.get('confidence', 0.0)),
			support_count=int(data.get('support_count', 0)),
		)


@dataclass(slots=True)
class RelationshipEdge:
	kind: str  # uses_token | contains | extends | pattern_uses
	source: str
	target: str
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'kind': self.kind,
			'source': self.source,
			'target': self.target,
			'metadata': dict(self.metadata),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> RelationshipEdge:
		return cls(
			kind=str(data.get('kind', '')),
			source=str(data.get('source', '')),
			target=str(data.get('target', '')),
			metadata=dict(data.get('metadata') or {}),
		)


@dataclass(slots=True)
class ExceptionNode:
	standard_id: str
	element_pattern: str
	actual_value: str
	rationale: str = ''
	approved_by: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'standard_id': self.standard_id,
			'element_pattern': self.element_pattern,
			'actual_value': self.actual_value,
			'rationale': self.rationale,
			'approved_by': self.approved_by,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> ExceptionNode:
		return cls(
			standard_id=str(data.get('standard_id', '')),
			element_pattern=str(data.get('element_pattern', '')),
			actual_value=str(data.get('actual_value', '')),
			rationale=str(data.get('rationale', '')),
			approved_by=data.get('approved_by'),
		)


@dataclass(slots=True)
class GraphConfidence:
	per_standard: dict[str, float] = field(default_factory=dict)
	overall: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'per_standard': dict(self.per_standard),
			'overall': self.overall,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any] | None) -> GraphConfidence:
		if not data:
			return cls()
		return cls(
			per_standard={str(k): float(v) for k, v in (data.get('per_standard') or {}).items()},
			overall=float(data.get('overall', 0.0)),
		)


@dataclass(slots=True)
class ProjectDesignGraph:
	"""Accumulated design-language knowledge for one project."""

	meta: GraphMeta
	foundations: FoundationsLayer = field(default_factory=FoundationsLayer)
	components: dict[str, ComponentNode] = field(default_factory=dict)
	patterns: dict[str, PatternNode] = field(default_factory=dict)
	relationships: list[RelationshipEdge] = field(default_factory=list)
	exceptions: list[ExceptionNode] = field(default_factory=list)
	confidence: GraphConfidence = field(default_factory=GraphConfidence)

	def to_dict(self) -> dict[str, Any]:
		return {
			'meta': self.meta.to_dict(),
			'foundations': self.foundations.to_dict(),
			'components': {k: v.to_dict() for k, v in self.components.items()},
			'patterns': {k: v.to_dict() for k, v in self.patterns.items()},
			'relationships': [r.to_dict() for r in self.relationships],
			'exceptions': [e.to_dict() for e in self.exceptions],
			'confidence': self.confidence.to_dict(),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> ProjectDesignGraph:
		components_raw = data.get('components') or {}
		patterns_raw = data.get('patterns') or {}
		return cls(
			meta=GraphMeta.from_dict(data.get('meta') or {}),
			foundations=FoundationsLayer.from_dict(data.get('foundations')),
			components={str(k): ComponentNode.from_dict(v) for k, v in components_raw.items()},
			patterns={str(k): PatternNode.from_dict(v) for k, v in patterns_raw.items()},
			relationships=[RelationshipEdge.from_dict(r) for r in data.get('relationships') or []],
			exceptions=[ExceptionNode.from_dict(e) for e in data.get('exceptions') or []],
			confidence=GraphConfidence.from_dict(data.get('confidence')),
		)

	def find_standard(self, standard_id: str) -> StandardNode | None:
		for s in self.foundations.standards:
			if s.id == standard_id:
				return s
		for comp in self.components.values():
			for s in comp.standards:
				if s.id == standard_id:
					return s
		return None

	def standards_for_context(self, context: str, *, property_name: str | None = None) -> list[StandardNode]:
		out: list[StandardNode] = []
		ctx = context.lower()
		for s in self.foundations.standards:
			if ctx in s.context.lower():
				if property_name is None or s.property == property_name:
					out.append(s)
		comp = self.components.get(context) or self.components.get(context.lower())
		if comp:
			for s in comp.standards:
				if property_name is None or s.property == property_name:
					out.append(s)
		return out


def empty_graph(
	project_id: str = 'default',
	*,
	repo_root: str = '',
) -> ProjectDesignGraph:
	"""Create an empty graph ready for Discovery Pipeline ingestion (Phase 2)."""
	version = new_graph_version()
	return ProjectDesignGraph(
		meta=GraphMeta(
			project_id=project_id,
			graph_version=version,
			learned_at=_utc_now(),
			snapshot_count=0,
			repo_root=repo_root,
			notes='Empty graph — run Discovery Pipeline to ingest knowledge (Phase 2).',
		),
	)
