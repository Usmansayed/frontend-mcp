"""Stable Consistency Intelligence contract for Component Intelligence."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import ConsistencyGuidance, FoundationSelection
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery

from .component_guidance import evaluate_component

MODULE_NAME = 'consistency_intelligence'


class ConsistencyIntelligenceAdapter:
	"""Public contract surface — implementation may evolve behind this API."""

	module_name = MODULE_NAME

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		parsed_query: ParsedQuery | None = None,
	) -> ConsistencyGuidance:
		return evaluate_component(candidate, repo_root=repo_root, parsed_query=parsed_query)

	def plan_consistency_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		repo_root: Path,
	) -> list[str]:
		_ = issue
		_ = repo_root
		actions: list[str] = []
		for mod in selection.guidance.consistency.all_adjustments()[:6]:
			actions.append(f'apply_{mod.category}:{mod.description}')
		return actions
