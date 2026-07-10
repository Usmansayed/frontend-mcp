"""Knowledge graph — links principles, patterns, heuristics (future Gemini research)."""
from __future__ import annotations

from ...models import ReviewRequest

_GRAPH: dict[str, list[str]] = {
	'checkout': ['progressive_disclosure', 'cognitive_load', 'ecommerce'],
	'sign in': ['recognition_over_recall', 'error_prevention', 'saas'],
	'dashboard': ['clear_hierarchy', 'information_density', 'dashboard'],
}


def query_relevant_concepts(request: ReviewRequest) -> list[str]:
	task = (request.user_task or '').lower()
	concepts: list[str] = []
	for key, nodes in _GRAPH.items():
		if key in task:
			concepts.extend(nodes)
	if request.scope == 'page':
		concepts.append('page_layout')
	return list(dict.fromkeys(concepts))
