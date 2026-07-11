"""Shared helpers for knowledge source collectors."""
from __future__ import annotations

from collections import Counter
from typing import Any

from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	PatternNode,
	ScaleCluster,
	StandardNode,
	TokenNode,
)


def standard_id(context: str, property_name: str) -> str:
	safe_ctx = context.replace(' ', '_').replace('.', '_').lower()
	safe_prop = property_name.replace(' ', '_').lower()
	return f'std_{safe_ctx}_{safe_prop}'


def value_distribution(values: list[Any]) -> tuple[list[str], dict[str, float], int]:
	if not values:
		return [], {}, 0
	str_vals = [str(v) for v in values]
	counts = Counter(str_vals)
	total = sum(counts.values())
	distribution = {k: round(v / total, 4) for k, v in counts.items()}
	expected = [k for k, _ in counts.most_common()]
	return expected, distribution, total


def confidence_from_support(support_count: int, *, base: float = 0.5) -> float:
	if support_count <= 0:
		return 0.0
	return min(0.99, base + min(support_count, 50) * 0.01)


def build_standard(
	*,
	context: str,
	property_name: str,
	values: list[Any],
	category: str = 'learned',
	provenance: str = 'learned',
	evidence_sample: list[str] | None = None,
) -> StandardNode | None:
	expected, distribution, support = value_distribution(values)
	if support == 0:
		return None
	return StandardNode(
		id=standard_id(context, property_name),
		category=category,
		context=context,
		property=property_name,
		expected_values=expected,
		distribution=distribution,
		confidence=confidence_from_support(support),
		support_count=support,
		provenance=provenance,
		evidence_sample=list(evidence_sample or [])[:8],
	)


def build_scale_cluster(
	name: str,
	values: list[Any],
	*,
	unit: str = 'px',
	provenance: str = 'learned',
) -> ScaleCluster | None:
	unique = sorted({str(v) for v in values if v is not None}, key=lambda x: float(x) if _is_numeric(x) else x)
	if not unique:
		return None
	return ScaleCluster(
		name=name,
		values=unique,
		unit=unit,
		confidence=confidence_from_support(len(values)),
		support_count=len(values),
	)


def _is_numeric(value: str) -> bool:
	try:
		float(value)
		return True
	except ValueError:
		return False


def infer_component_from_node(node: dict[str, Any]) -> tuple[str, list[str]]:
	tag = str(node.get('tag') or '').lower()
	classes = [str(c) for c in (node.get('classes') or [])]
	role = str(node.get('role') or '').lower()

	if tag == 'button' or role == 'button':
		name = 'button'
	elif tag in ('input', 'select', 'textarea'):
		name = tag
	elif tag == 'a' or role == 'link':
		name = 'link'
	else:
		name = tag or 'element'

	variants: list[str] = []
	for cls in classes:
		lower = cls.lower()
		if lower in ('primary', 'secondary', 'ghost', 'outline', 'destructive', 'default', 'sm', 'lg', 'md'):
			variants.append(lower)
	return name, variants


def merge_component_nodes(existing: ComponentNode, incoming: ComponentNode) -> ComponentNode:
	variant_set = list(dict.fromkeys([*existing.variants, *incoming.variants]))
	state_set = list(dict.fromkeys([*existing.states, *incoming.states]))
	standards_by_id = {s.id: s for s in existing.standards}
	for s in incoming.standards:
		if s.id in standards_by_id:
			standards_by_id[s.id] = _merge_standard_nodes(standards_by_id[s.id], s)
		else:
			standards_by_id[s.id] = s
	support = existing.support_count + incoming.support_count
	conf = max(existing.confidence, incoming.confidence)
	canonical = existing.canonical_variant or incoming.canonical_variant
	if not canonical and variant_set:
		canonical = variant_set[0]
	return ComponentNode(
		name=existing.name,
		variants=variant_set,
		states=state_set,
		standards=list(standards_by_id.values()),
		support_count=support,
		confidence=conf,
		canonical_variant=canonical,
	)


def _merge_standard_nodes(existing: StandardNode, incoming: StandardNode) -> StandardNode:
	combined_counts: Counter[str] = Counter()
	for val, weight in existing.distribution.items():
		combined_counts[val] += weight * max(existing.support_count, 1)
	for val, weight in incoming.distribution.items():
		combined_counts[val] += weight * max(incoming.support_count, 1)
	total = sum(combined_counts.values()) or 1
	distribution = {k: round(v / total, 4) for k, v in combined_counts.items()}
	support = existing.support_count + incoming.support_count
	expected = [k for k, _ in combined_counts.most_common()]
	winner = existing if existing.confidence >= incoming.confidence else incoming
	evidence = list(dict.fromkeys([*existing.evidence_sample, *incoming.evidence_sample]))[:12]
	return StandardNode(
		id=existing.id,
		category=winner.category,
		context=existing.context,
		property=existing.property,
		expected_values=expected,
		distribution=distribution,
		confidence=max(existing.confidence, incoming.confidence),
		support_count=support,
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


def pattern_from_snapshot(name: str, count: int, *, description: str = '') -> PatternNode:
	return PatternNode(
		name=name,
		description=description or f'Observed {count} instance(s) in design snapshot.',
		confidence=confidence_from_support(count),
		support_count=count,
	)
