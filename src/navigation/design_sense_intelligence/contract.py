"""Stable Design Sense Intelligence contract for Component Intelligence."""
from __future__ import annotations

from navigation.component_intelligence.integration_models import DesignSenseGuidance, FoundationSelection
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery

from .component_guidance import evaluate_component

MODULE_NAME = 'design_sense_intelligence'


class DesignSenseIntelligenceAdapter:
	"""Public contract surface — implementation may evolve behind this API."""

	module_name = MODULE_NAME

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		parsed_query: ParsedQuery | None = None,
	) -> DesignSenseGuidance:
		return evaluate_component(candidate, parsed_query=parsed_query)

	def plan_design_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
	) -> list[str]:
		_ = issue
		actions: list[str] = []
		g = selection.guidance.design_sense
		if g.layout_recommendation:
			actions.append(f'apply_layout:{g.layout_recommendation}')
		if g.interaction_recommendation:
			actions.append(f'apply_interaction:{g.interaction_recommendation}')
		for note in g.notes[:2]:
			actions.append(f'address_ux_note:{note}')
		return actions
