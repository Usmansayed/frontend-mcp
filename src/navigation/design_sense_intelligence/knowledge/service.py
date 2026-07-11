"""First-class design knowledge — structured from Gemini research."""
from __future__ import annotations

from ..models import ProviderContribution, ReviewFinding, ReviewRequest
from .catalog import KNOWLEDGE_TOPICS, TOPIC_BY_ID
from .evaluation_rules import evaluate_against_rules
from .knowledge_graph import query_relevant_concepts
from .pattern_library import match_patterns
from .principles import get_applicable_principles
from .psychology import get_psychology_hints


class KnowledgeService:
	"""Consult internal knowledge before subjective synthesis."""

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		findings: list[ReviewFinding] = []
		notes: list[str] = []
		degraded: list[str] = []

		for principle in get_applicable_principles(request):
			notes.append(f'principle:{principle["id"]}')
			if principle.get('finding'):
				findings.append(principle['finding'])

		for hint in get_psychology_hints(request):
			notes.append(f'psychology:{hint["id"]}:{hint["title"]}')

		for pattern in match_patterns(request):
			notes.append(f'pattern:{pattern["category"]}:{pattern["id"]}')
			if pattern.get('recommendation'):
				notes.append(f'recommend:{pattern["recommendation"]}')

		findings.extend(evaluate_against_rules(request))
		concepts = query_relevant_concepts(request)
		notes.extend(concepts)

		# Surface matched catalog topics as notes
		task = (request.user_task or '').lower()
		for topic in KNOWLEDGE_TOPICS:
			if any(kw in task for kw in topic.keywords):
				notes.append(f'catalog:{topic.section}:{topic.title}')

		if not findings and not concepts:
			degraded.append('design_knowledge_no_task_match')
		else:
			degraded.append('design_knowledge_structured')

		return ProviderContribution(
			provider='design_knowledge',
			findings=findings,
			notes=notes,
			degraded=degraded,
		)

	def get_topic(self, topic_id: str):
		return TOPIC_BY_ID.get(topic_id)

	def list_topics(self) -> list[dict]:
		return [
			{'id': t.id, 'section': t.section, 'title': t.title, 'category': t.category}
			for t in KNOWLEDGE_TOPICS
		]
