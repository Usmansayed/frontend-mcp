"""Stable Codebase Intelligence contract for Component Intelligence."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import CodebaseGuidance, FoundationSelection
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery

from .component_guidance import evaluate_component

MODULE_NAME = 'codebase_intelligence'


class CodebaseIntelligenceAdapter:
	"""Public contract surface — implementation may evolve behind this API."""

	module_name = MODULE_NAME

	def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		parsed_query: ParsedQuery | None = None,
	) -> CodebaseGuidance:
		return evaluate_component(candidate, repo_root=repo_root, parsed_query=parsed_query)

	def plan_codebase_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		repo_root: Path,
	) -> list[str]:
		_ = issue
		_ = repo_root
		actions: list[str] = []
		for hint in selection.guidance.codebase.preferred_implementations[:3]:
			actions.append(f'apply_codebase_pattern:{hint}')
		for util in selection.guidance.codebase.reusable_utilities[:2]:
			actions.append(f'use_utility:{util}')
		for dup in selection.guidance.codebase.duplicate_risks[:2]:
			actions.append(f'resolve_duplicate:{dup}')
		return actions
