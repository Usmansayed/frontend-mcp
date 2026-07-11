"""Knowledge graph — topic relationships from Gemini research."""
from __future__ import annotations

from ...models import ReviewRequest
from ..catalog import KNOWLEDGE_TOPICS, TOPIC_BY_ID
from ..epistemology import NIELSEN_HEURISTICS

# Task/context → topic IDs
_TASK_GRAPH: dict[str, list[str]] = {
	'checkout': ['user_flows', 'forms', 'ecommerce_design', 'cognitive_psychology'],
	'sign in': ['forms', 'saas_design', 'usability', 'wcag_accessibility'],
	'login': ['forms', 'saas_design', 'usability'],
	'dashboard': ['dashboards', 'tables', 'visual_hierarchy', 'enterprise_design'],
	'landing': ['landing_pages', 'visual_hierarchy', 'color_theory'],
	'mobile': ['mobile_design', 'responsive_design', 'touch'],
	'cart': ['ecommerce_design', 'user_flows'],
	'onboard': ['saas_design', 'user_flows', 'ui_states'],
	'admin': ['enterprise_design', 'tables', 'information_architecture'],
	'form': ['forms', 'interaction_design', 'ui_states'],
}

# Topic → related Nielsen heuristic IDs
_TOPIC_TO_HEURISTICS: dict[str, list[str]] = {
	'forms': ['nielsen_h5', 'nielsen_h9'],
	'navigation': ['nielsen_h4', 'nielsen_h6'],
	'ui_states': ['nielsen_h1', 'nielsen_h9'],
	'usability': ['nielsen_h3', 'nielsen_h5'],
	'interaction_design': ['nielsen_h1', 'nielsen_h7'],
}

_HEURISTIC_BY_ID = {h.id: h for h in NIELSEN_HEURISTICS}


def query_relevant_concepts(request: ReviewRequest) -> list[str]:
	task = (request.user_task or '').lower()
	concepts: list[str] = []

	for keyword, topic_ids in _TASK_GRAPH.items():
		if keyword in task:
			for tid in topic_ids:
				topic = TOPIC_BY_ID.get(tid)
				if topic:
					concepts.append(f'topic:{topic.id}')
					concepts.extend(f'rule:{r[:40]}' for r in topic.key_rules[:2])

	for topic in _match_topics_by_keywords(task, request):
		concepts.append(f'topic:{topic.id}')
		for hid in _TOPIC_TO_HEURISTICS.get(topic.id, [])[:2]:
			h = _HEURISTIC_BY_ID.get(hid)
			if h:
				concepts.append(f'heuristic:{h.id}')

	if request.scope == 'page':
		concepts.append('topic:layout_systems')
	if request.computed_styles:
		concepts.append('topic:design_tokens')

	return list(dict.fromkeys(concepts))[:12]


def _match_topics_by_keywords(task: str, request: ReviewRequest) -> list:
	matched = []
	for topic in KNOWLEDGE_TOPICS:
		if any(kw in task for kw in topic.keywords):
			matched.append(topic)
	if not matched and request.scope:
		for topic in KNOWLEDGE_TOPICS:
			if topic.category in (request.scope,):
				matched.append(topic)
				break
	return matched[:5]
