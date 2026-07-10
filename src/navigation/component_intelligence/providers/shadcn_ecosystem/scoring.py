"""Provider-local relevance scoring for registry items."""
from __future__ import annotations

import re
from typing import Any

from ...models import ParsedQuery, PlannedQuery


def score_item(
	item: dict[str, Any],
	parsed: ParsedQuery,
	*,
	planned_query: PlannedQuery | None = None,
) -> float:
	query_text = planned_query.text if planned_query else parsed.raw
	tokens = _tokens(query_text)
	if not tokens:
		return 0.0

	fields = ' '.join(
		str(item.get(key) or '')
		for key in ('name', 'title', 'description', 'type', 'categories', 'tags')
	).lower()
	name = str(item.get('name') or '').lower()
	title = str(item.get('title') or '').lower()
	description = str(item.get('description') or '').lower()

	score = 0.0
	for token in tokens:
		if token in name:
			score += 3.0
		elif token in title:
			score += 2.0
		elif token in description:
			score += 1.0
		elif token in fields:
			score += 0.5

	for comp in parsed.component_types:
		if comp in name or comp in title or comp in description:
			score += 2.5
	for page in parsed.page_types + parsed.page_context:
		if page in name or page in title or page in description:
			score += 2.0
	for style in parsed.styles:
		if style in fields:
			score += 1.5
	if parsed.theme and parsed.theme in fields:
		score += 1.0
	for anim in parsed.animations:
		if anim in fields:
			score += 1.0
	for hint in parsed.search_hints:
		if hint in fields or hint in name:
			score += 1.0

	item_type = str(item.get('type') or '')
	if parsed.page_context and 'block' in item_type:
		score += 0.75

	if planned_query is not None:
		score *= planned_query.confidence

	max_score = max(len(tokens) * 3.0, 1.0)
	return min(score / max_score, 1.0)


def _tokens(text: str) -> list[str]:
	return [tok for tok in re.findall(r'[a-z0-9]+', text.lower()) if len(tok) > 1]
