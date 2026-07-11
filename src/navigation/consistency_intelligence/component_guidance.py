"""Consistency Intelligence guidance — queries Project Design Graph via Knowledge API."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import ConsistencyGuidance, ModificationHint
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.graph.persistence import GraphStore


def evaluate_component(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
) -> ConsistencyGuidance:
	_ = parsed_query
	api = KnowledgeAPI(GraphStore(storage_root=repo_root))
	name = candidate.name.lower()
	degraded: list[str] = []

	variants = api.query('component.variants', {'component': name})
	spacing = api.query('spacing.system', {})
	tokens = api.query('tokens.declared', {})
	canonical = api.query('component.canonical', {'component': name})
	similar = api.query('component.similar', {'component': name})

	required: list[ModificationHint] = []
	token_hints: list[ModificationHint] = []
	spacing_hints: list[ModificationHint] = []
	typography_hints: list[ModificationHint] = []
	color_hints: list[ModificationHint] = []
	radius_hints: list[ModificationHint] = []
	shadow_hints: list[ModificationHint] = []

	if variants.answer.get('status') == 'ok':
		for std in variants.standards:
			if std.expected_values:
				required.append(
					ModificationHint(
						category=std.category or 'consistency',
						description=f"Align {std.property_name} with project standard",
						to_value=std.expected_values[0],
						required=False,
					)
				)
	else:
		degraded.append('component_not_in_graph')

	if spacing.answer.get('scales'):
		spacing_hints.append(
			ModificationHint(
				category='spacing',
				description='Use project spacing scale from design graph',
				required=False,
			)
		)

	if tokens.answer.get('count'):
		token_hints.append(
			ModificationHint(
				category='token',
				description=f"Map styles to {tokens.answer['count']} declared project tokens",
				required=False,
			)
		)

	if canonical.answer.get('canonical_variant'):
		required.append(
			ModificationHint(
				category='variant',
				description=f"Prefer canonical variant `{canonical.answer['canonical_variant']}`",
				to_value=canonical.answer['canonical_variant'],
				required=False,
			)
		)

	if similar.answer.get('similar'):
		degraded.append(f"similar_components:{len(similar.answer['similar'])}")

	if not required and not token_hints:
		degraded.append('graph_empty_or_candidate_unknown')

	return ConsistencyGuidance(
		required_modifications=required,
		token_adjustments=token_hints,
		spacing_adjustments=spacing_hints,
		typography_adjustments=typography_hints,
		color_adjustments=color_hints,
		radius_adjustments=radius_hints,
		shadow_adjustments=shadow_hints,
		degraded=degraded,
	)
