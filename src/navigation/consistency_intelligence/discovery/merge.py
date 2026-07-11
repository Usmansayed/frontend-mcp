"""Merge knowledge fragments into the Project Design Graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from navigation.consistency_intelligence.discovery.collect_helpers import merge_component_nodes
from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	ExceptionNode,
	FoundationsLayer,
	GraphConfidence,
	PatternNode,
	ProjectDesignGraph,
	RelationshipEdge,
	ScaleCluster,
	StandardNode,
	TokenNode,
)
from navigation.consistency_intelligence.graph.version import new_graph_version

from .sources.protocol import KnowledgeFragment


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class MergeStats:
	sources_merged: list[str] = field(default_factory=list)
	standards_added: int = 0
	standards_updated: int = 0
	tokens_added: int = 0
	tokens_updated: int = 0
	components_added: int = 0
	components_updated: int = 0
	patterns_added: int = 0
	patterns_updated: int = 0
	relationships_added: int = 0
	exceptions_added: int = 0
	snapshot_ingested: bool = False

	def to_dict(self) -> dict[str, Any]:
		return {
			'sources_merged': list(self.sources_merged),
			'standards_added': self.standards_added,
			'standards_updated': self.standards_updated,
			'tokens_added': self.tokens_added,
			'tokens_updated': self.tokens_updated,
			'components_added': self.components_added,
			'components_updated': self.components_updated,
			'patterns_added': self.patterns_added,
			'patterns_updated': self.patterns_updated,
			'relationships_added': self.relationships_added,
			'exceptions_added': self.exceptions_added,
			'snapshot_ingested': self.snapshot_ingested,
		}


def merge_fragments(
	graph: ProjectDesignGraph,
	fragments: list[KnowledgeFragment],
) -> tuple[ProjectDesignGraph, MergeStats]:
	stats = MergeStats()
	for fragment in fragments:
		if not _fragment_has_data(fragment):
			continue
		stats.sources_merged.append(fragment.source_id)
		if fragment.source_id == 'snapshot':
			stats.snapshot_ingested = True
		_merge_standards(graph, fragment.standards, stats)
		_merge_tokens(graph, fragment.tokens, stats)
		_merge_components(graph, fragment.components, stats)
		_merge_patterns(graph, fragment.patterns, stats)
		_merge_relationships(graph, fragment.relationships, stats)
		_merge_exceptions(graph, fragment.exceptions, stats)
		_merge_scales(graph.foundations, fragment)

	_recompute_confidence(graph)
	graph.meta.graph_version = new_graph_version()
	graph.meta.learned_at = _utc_now()
	if stats.snapshot_ingested:
		graph.meta.snapshot_count += 1
	if stats.sources_merged:
		graph.meta.notes = (
			f'Graph updated from sources: {", ".join(stats.sources_merged)} '
			f'at {graph.meta.learned_at}.'
		)
	return graph, stats


def _fragment_has_data(fragment: KnowledgeFragment) -> bool:
	return bool(
		fragment.standards
		or fragment.tokens
		or fragment.components
		or fragment.patterns
		or fragment.relationships
		or fragment.exceptions
	)


def _merge_standards(graph: ProjectDesignGraph, standards: list[StandardNode], stats: MergeStats) -> None:
	by_id = {s.id: s for s in graph.foundations.standards}
	for std in standards:
		if std.id in by_id:
			merged = _merge_standard(by_id[std.id], std)
			by_id[std.id] = merged
			stats.standards_updated += 1
		else:
			by_id[std.id] = std
			stats.standards_added += 1
	graph.foundations.standards = list(by_id.values())


def _merge_standard(existing: StandardNode, incoming: StandardNode) -> StandardNode:
	if incoming.provenance == 'declared' and existing.provenance == 'learned':
		return incoming
	if existing.provenance == 'declared' and incoming.provenance == 'learned':
		return existing
	if incoming.support_count > existing.support_count:
		winner = incoming
	elif existing.support_count > incoming.support_count:
		winner = existing
	else:
		winner = incoming if incoming.confidence >= existing.confidence else existing

	combined_support = existing.support_count + incoming.support_count
	combined_dist: dict[str, float] = {}
	for val in set(existing.distribution) | set(incoming.distribution):
		ew = existing.distribution.get(val, 0.0) * max(existing.support_count, 1)
		iw = incoming.distribution.get(val, 0.0) * max(incoming.support_count, 1)
		combined_dist[val] = ew + iw
	total = sum(combined_dist.values()) or 1.0
	distribution = {k: round(v / total, 4) for k, v in combined_dist.items()}
	expected = sorted(distribution.keys(), key=lambda k: distribution[k], reverse=True)
	evidence = list(dict.fromkeys([*existing.evidence_sample, *incoming.evidence_sample]))[:12]

	return StandardNode(
		id=existing.id,
		category=winner.category,
		context=existing.context,
		property=existing.property,
		expected_values=expected,
		distribution=distribution,
		confidence=max(existing.confidence, incoming.confidence),
		support_count=combined_support,
		provenance=_merge_provenance(existing.provenance, incoming.provenance),
		evidence_sample=evidence,
	)


def _merge_provenance(a: str, b: str) -> str:
	if 'declared' in (a, b):
		return 'declared'
	if 'user' in (a, b):
		return 'user'
	if a == 'merged' or b == 'merged':
		return 'merged'
	return 'learned'


def _merge_tokens(graph: ProjectDesignGraph, tokens: list[TokenNode], stats: MergeStats) -> None:
	by_path = {t.path_str: t for t in graph.foundations.color_tokens}
	by_path.update({t.path_str: t for t in graph.foundations.shadow_tokens})
	by_path.update({t.path_str: t for t in graph.foundations.motion_tokens})

	for token in tokens:
		key = token.path_str
		if key in by_path:
			existing = by_path[key]
			if existing.provenance == 'declared' and token.provenance == 'learned':
				stats.tokens_updated += 1
				continue
			if token.provenance == 'declared' or token.confidence > existing.confidence:
				by_path[key] = token
			stats.tokens_updated += 1
		else:
			by_path[key] = token
			stats.tokens_added += 1

	color_tokens: list[TokenNode] = []
	shadow_tokens: list[TokenNode] = []
	motion_tokens: list[TokenNode] = []
	for token in by_path.values():
		path_head = token.path[0] if token.path else ''
		if path_head in ('shadow', 'elevation'):
			shadow_tokens.append(token)
		elif path_head in ('motion', 'duration', 'easing'):
			motion_tokens.append(token)
		else:
			color_tokens.append(token)

	graph.foundations.color_tokens = color_tokens
	graph.foundations.shadow_tokens = shadow_tokens
	graph.foundations.motion_tokens = motion_tokens


def _merge_components(graph: ProjectDesignGraph, components: dict[str, ComponentNode], stats: MergeStats) -> None:
	for name, incoming in components.items():
		key = name.lower()
		existing = graph.components.get(key)
		if existing is None:
			graph.components[key] = incoming
			stats.components_added += 1
		else:
			graph.components[key] = merge_component_nodes(existing, incoming)
			stats.components_updated += 1


def _merge_patterns(graph: ProjectDesignGraph, patterns: dict[str, PatternNode], stats: MergeStats) -> None:
	for name, incoming in patterns.items():
		key = name.lower()
		existing = graph.patterns.get(key)
		if existing is None:
			graph.patterns[key] = incoming
			stats.patterns_added += 1
		else:
			graph.patterns[key] = PatternNode(
				name=existing.name,
				description=incoming.description or existing.description,
				component_refs=list(dict.fromkeys([*existing.component_refs, *incoming.component_refs])),
				confidence=max(existing.confidence, incoming.confidence),
				support_count=existing.support_count + incoming.support_count,
			)
			stats.patterns_updated += 1


def _merge_relationships(graph: ProjectDesignGraph, relationships: list[RelationshipEdge], stats: MergeStats) -> None:
	seen = {(r.kind, r.source, r.target) for r in graph.relationships}
	for edge in relationships:
		key = (edge.kind, edge.source, edge.target)
		if key not in seen:
			graph.relationships.append(edge)
			seen.add(key)
			stats.relationships_added += 1


def _merge_exceptions(graph: ProjectDesignGraph, exceptions: list[ExceptionNode], stats: MergeStats) -> None:
	seen = {(e.standard_id, e.element_pattern, e.actual_value) for e in graph.exceptions}
	for exc in exceptions:
		key = (exc.standard_id, exc.element_pattern, exc.actual_value)
		if key not in seen:
			graph.exceptions.append(exc)
			seen.add(key)
			stats.exceptions_added += 1


def _merge_scales(foundations: FoundationsLayer, fragment: KnowledgeFragment) -> None:
	"""Scale clusters arrive via fragment metadata in evidence or dedicated token paths."""
	# Scales are attached to foundations via snapshot/tokens collectors using graph fields
	# on the fragment's standards path — snapshot collector sets foundations inline on graph
	# via standards; scale clusters merged here from fragment evidence extensions.
	for item in fragment.evidence:
		if not isinstance(item, dict):
			continue
		kind = item.get('kind')
		if kind == 'typography_scale':
			cluster = ScaleCluster.from_dict(item.get('cluster') or {})
			if cluster.values:
				_merge_scale_list(foundations.typography_scale, cluster)
		elif kind == 'spacing_scale':
			cluster = ScaleCluster.from_dict(item.get('cluster') or {})
			if cluster.values:
				_merge_scale_list(foundations.spacing_scale, cluster)
		elif kind == 'radius_scale':
			cluster = ScaleCluster.from_dict(item.get('cluster') or {})
			if cluster.values:
				_merge_scale_list(foundations.radius_scale, cluster)


def _merge_scale_list(existing: list[ScaleCluster], incoming: ScaleCluster) -> None:
	for i, cluster in enumerate(existing):
		if cluster.name == incoming.name:
			values = sorted(set(cluster.values) | set(incoming.values), key=_scale_sort_key)
			existing[i] = ScaleCluster(
				name=cluster.name,
				values=values,
				unit=incoming.unit or cluster.unit,
				confidence=max(cluster.confidence, incoming.confidence),
				support_count=cluster.support_count + incoming.support_count,
			)
			return
	existing.append(incoming)


def _scale_sort_key(value: str) -> float:
	try:
		return float(value)
	except ValueError:
		return 0.0


def _recompute_confidence(graph: ProjectDesignGraph) -> None:
	per_standard: dict[str, float] = {}
	all_standards: list[StandardNode] = list(graph.foundations.standards)
	for comp in graph.components.values():
		all_standards.extend(comp.standards)
	for std in all_standards:
		per_standard[std.id] = std.confidence
	overall = sum(per_standard.values()) / len(per_standard) if per_standard else 0.0
	graph.confidence = GraphConfidence(per_standard=per_standard, overall=round(overall, 4))
