"""Knowledge API query catalog."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuerySpec:
	query_id: str
	description: str
	category: str
	params: tuple[str, ...] = ()
	phase: int = 1


QUERY_CATALOG: tuple[QuerySpec, ...] = (
	# Foundations
	QuerySpec('standard.for_context', 'Standard property values for a UI context', 'foundations', ('context', 'property')),
	QuerySpec('typography.scale', 'Learned typography scale for this project', 'foundations'),
	QuerySpec('spacing.system', 'Learned spacing scale', 'foundations'),
	QuerySpec('radius.scale', 'Learned border-radius scale', 'foundations'),
	QuerySpec('color.palette', 'Semantic color roles and tokens', 'foundations'),
	# Components
	QuerySpec('component.variants', 'All variants of a component type', 'components', ('component',)),
	QuerySpec('component.canonical', 'Canonical variant for a component', 'components', ('component',)),
	QuerySpec('component.similar', 'Most similar component to a reference', 'components', ('component', 'selector')),
	QuerySpec('component.states', 'Interaction states observed for a component', 'components', ('component',)),
	# Tokens
	QuerySpec('tokens.declared', 'Declared design tokens in graph', 'tokens'),
	QuerySpec('tokens.used', 'Tokens referenced in implementation', 'tokens'),
	QuerySpec('tokens.unused', 'Declared but unused tokens', 'tokens'),
	QuerySpec('tokens.fragmentation', 'Near-duplicate token values', 'tokens'),
	# Consistency (Phase 3 consumers — stubs in Phase 1)
	QuerySpec('consistency.explain', 'Why an element deviates from standards', 'consistency', ('selector',), phase=3),
	QuerySpec('consistency.assess', 'Assess element consistency', 'consistency', ('selector',), phase=3),
	QuerySpec('fix.recommend', 'Recommended fix for a deviation', 'consistency', ('standard_id', 'selector'), phase=3),
	QuerySpec('confidence.for', 'Confidence for a standard or assessment', 'consistency', ('standard_id',), phase=2),
	# Exceptions & meta
	QuerySpec('exceptions.for', 'Exceptions for a standard', 'exceptions', ('standard_id',)),
	QuerySpec('exceptions.list', 'All project exceptions', 'exceptions'),
	QuerySpec('graph.summary', 'High-level project design language overview', 'graph'),
	QuerySpec('graph.diff', 'Diff graph vs prior version', 'graph', ('other_version',)),
)

QUERY_BY_ID = {q.query_id: q for q in QUERY_CATALOG}
