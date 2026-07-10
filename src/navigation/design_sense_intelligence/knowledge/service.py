"""First-class design knowledge — Gemini research and curated references live here."""
from __future__ import annotations

from ..models import ProviderContribution, ReviewFinding, ReviewRequest
from .evaluation_rules import evaluate_against_rules
from .knowledge_graph import query_relevant_concepts
from .pattern_library import match_patterns
from .principles import get_applicable_principles
from .psychology import get_psychology_hints

MODULE_NAME = 'design_knowledge'


class KnowledgeService:
	"""Consult internal knowledge before subjective synthesis."""

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		findings: list[ReviewFinding] = []
		notes: list[str] = []
		degraded = ['design_knowledge_heuristic']

		for principle in get_applicable_principles(request):
			notes.append(f'principle:{principle["id"]}')
			if principle.get('finding'):
				findings.append(principle['finding'])

		for hint in get_psychology_hints(request):
			notes.append(f'psychology:{hint["id"]}')

		patterns = match_patterns(request)
		for pattern in patterns:
			notes.append(f'pattern:{pattern["category"]}:{pattern["id"]}')
			if pattern.get('recommendation'):
				notes.append(f'recommend:{pattern["recommendation"]}')

		findings.extend(evaluate_against_rules(request))
		concepts = query_relevant_concepts(request)
		notes.extend(f'concept:{c}' for c in concepts[:5])

		return ProviderContribution(
			provider=MODULE_NAME,
			findings=findings,
			notes=notes,
			degraded=degraded,
		)
