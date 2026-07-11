"""Core design principles — from knowledge catalog and Nielsen heuristics."""
from __future__ import annotations

from ...models import ReviewFinding, ReviewRequest
from ..catalog import KNOWLEDGE_TOPICS, TOPIC_BY_ID

_SCOPE_TOPICS: dict[str, list[str]] = {
	'page': ['layout_systems', 'visual_hierarchy'],
	'feature': ['layout_systems', 'design_patterns'],
	'flow': ['user_flows', 'progressive_disclosure'],
	'component': ['components', 'ui_states'],
}

# Alias for progressive_disclosure from interaction concepts
_TOPIC_ALIASES = {
	'progressive_disclosure': 'interaction_design',
	'components': 'design_patterns',
}


def get_applicable_principles(request: ReviewRequest) -> list[dict]:
	out: list[dict] = []
	task = (request.user_task or '').lower()
	seen: set[str] = set()

	# Scope-based topics (notes only — findings require snapshot evidence)
	for tid in _SCOPE_TOPICS.get(request.scope, []):
		resolved = _TOPIC_ALIASES.get(tid, tid)
		topic = TOPIC_BY_ID.get(resolved)
		if topic and topic.id not in seen:
			seen.add(topic.id)
			out.append(_topic_to_principle(topic, include_finding=False))

	# Task-keyword topics
	for topic in KNOWLEDGE_TOPICS:
		if topic.id in seen:
			continue
		if any(kw in task for kw in topic.keywords):
			seen.add(topic.id)
			out.append(_topic_to_principle(topic, include_finding=False))

	return out[:10]


def _topic_to_principle(topic, *, include_finding: bool = False) -> dict:
	entry: dict = {'id': topic.id, 'title': topic.title}
	if include_finding and topic.key_rules:
		entry['finding'] = ReviewFinding(
			id=f'principle_{topic.id}',
			category=topic.category,
			severity='advisory',
			message=topic.key_rules[0],
			rationale=topic.definition[:200],
			recommendation=topic.evaluation_criteria or '',
			source='design_knowledge',
		)
	return entry
