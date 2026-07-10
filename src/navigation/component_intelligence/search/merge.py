"""Merge and deduplicate component search results."""
from __future__ import annotations

from ..models import ComponentCandidate


def merge_candidates(
	existing: list[ComponentCandidate],
	new_items: list[ComponentCandidate],
) -> list[ComponentCandidate]:
	by_id: dict[str, ComponentCandidate] = {}
	for candidate in existing:
		by_id[candidate.id] = candidate

	for candidate in new_items:
		current = by_id.get(candidate.id)
		if current is None:
			by_id[candidate.id] = candidate
			continue
		if candidate.relevance_score > current.relevance_score:
			merged_sources = list(current.metadata.get('sources') or [])
			if candidate.metadata.get('matched_query'):
				merged_sources.append(
					{
						'provider': candidate.provider,
						'matched_query': candidate.metadata.get('matched_query'),
						'pass_number': candidate.metadata.get('search_pass'),
						'confidence': candidate.metadata.get('plan_confidence'),
					}
				)
			candidate.metadata['sources'] = merged_sources
			by_id[candidate.id] = candidate
		else:
			sources = list(current.metadata.get('sources') or [])
			if candidate.metadata.get('matched_query'):
				sources.append(
					{
						'provider': candidate.provider,
						'matched_query': candidate.metadata.get('matched_query'),
						'pass_number': candidate.metadata.get('search_pass'),
						'confidence': candidate.metadata.get('plan_confidence'),
					}
				)
			current.metadata['sources'] = sources

	merged = list(by_id.values())
	merged.sort(key=lambda c: c.relevance_score, reverse=True)
	return merged


def is_sufficient(
	candidates: list[ComponentCandidate],
	*,
	min_count: int = 8,
	min_score: float = 0.35,
	min_registries: int = 3,
) -> bool:
	good = [c for c in candidates if c.relevance_score >= min_score]
	if len(good) < min_count:
		return False
	registries = {c.registry for c in good if c.registry}
	return len(registries) >= min_registries
