"""Candidate filtering before cross-module guidance."""
from __future__ import annotations

from ..models import ComponentCandidate

DEFAULT_MIN_SCORE = 0.12
PREFER_BLOCK_FOR_PAGE_CONTEXT = True


def filter_candidates(
	candidates: list[ComponentCandidate],
	*,
	min_score: float = DEFAULT_MIN_SCORE,
	max_count: int = 12,
	page_context: list[str] | None = None,
) -> list[ComponentCandidate]:
	"""Reduce search results to a guidance-sized shortlist."""
	if not candidates:
		return []

	scored = [c for c in candidates if c.relevance_score >= min_score]
	scored.sort(key=lambda c: c.relevance_score, reverse=True)

	if page_context and PREFER_BLOCK_FOR_PAGE_CONTEXT:
		blocks = [c for c in scored if c.category == 'block' or 'block' in (c.item_type or '')]
		primitives = [c for c in scored if c not in blocks]
		scored = blocks + primitives

	seen_names: set[str] = set()
	deduped: list[ComponentCandidate] = []
	for candidate in scored:
		key = f'{candidate.registry}:{candidate.name}'.lower()
		if key in seen_names:
			continue
		seen_names.add(key)
		deduped.append(candidate)
		if len(deduped) >= max_count:
			break
	return deduped
