"""Selection Planner — decides who is worth opening, not who ranks highest."""
from __future__ import annotations

import re

from navigation.figma_intelligence.models import FigmaRankedCandidate
from navigation.figma_intelligence.selection.models import (
	SelectedCandidate,
	SelectionBudget,
	SelectionPlan,
)

_DESIGN_SYSTEM_STOPWORDS = frozenset(
	{'ui', 'kit', 'template', 'design', 'system', 'figma', 'community', 'free', 'the', 'and', 'for'}
)


def build_selection_plan(
	ranked: list[FigmaRankedCandidate],
	*,
	budget: SelectionBudget | None = None,
) -> SelectionPlan:
	"""Budget-aware progressive retrieval plan.

	Batch 1: open top N immediately.
	Batch 2+: open next M if confidence below threshold.
	Deduplicate templates from the same design system family.
	"""
	budget = budget or SelectionBudget()
	degraded: list[str] = []
	if not ranked:
		degraded.append('selection_empty_ranked_pool')
		return SelectionPlan(degraded=degraded, budget=budget)

	selected: list[SelectedCandidate] = []
	seen_systems: set[str] = set()
	reserve: list[FigmaRankedCandidate] = []

	def try_add(item: FigmaRankedCandidate, batch: int, reason: str) -> bool:
		if len(selected) >= budget.max_total_open:
			return False
		ds_key = _design_system_key(item)
		if ds_key and ds_key in seen_systems:
			return False
		if ds_key:
			seen_systems.add(ds_key)
		selected.append(
			SelectedCandidate(
				ranked=item,
				batch_number=batch,
				open_reason=reason,
				design_system_key=ds_key,
			)
		)
		return True

	# Batch 1 — immediate opens.
	for item in ranked:
		if len([s for s in selected if s.batch_number == 1]) >= budget.initial_open:
			break
		try_add(item, 1, 'top_ranked_immediate')

	# Reserve pool (not opened yet).
	for item in ranked:
		if any(s.ranked.candidate.candidate_id == item.candidate.candidate_id for s in selected):
			continue
		reserve.append(item)

	best_score = ranked[0].overall_score if ranked else 0.0
	needs_fallback = best_score < budget.confidence_stop_threshold

	if needs_fallback and reserve:
		opened = 0
		for item in reserve:
			if opened >= budget.fallback_open:
				break
			if try_add(item, 2, 'confidence_below_threshold'):
				opened += 1
		if opened == 0:
			degraded.append('selection_fallback_skipped_duplicates')
	elif not needs_fallback:
		degraded.append('selection_batch1_sufficient_confidence')

	remaining_reserve = [
		item
		for item in reserve
		if not any(s.ranked.candidate.candidate_id == item.candidate.candidate_id for s in selected)
	]

	return SelectionPlan(
		selected=selected,
		reserve=remaining_reserve,
		budget=budget,
		stop_when_confidence_met=True,
		degraded=degraded,
	)


def _design_system_key(item: FigmaRankedCandidate) -> str:
	meta = item.candidate.metadata
	for key in ('design_system', 'design_system_key', 'library_name', 'author'):
		val = meta.get(key)
		if isinstance(val, str) and val.strip():
			return _slug(val)

	title = item.candidate.title.lower()
	tokens = [t for t in re.split(r'[\s\-_|]+', title) if t and t not in _DESIGN_SYSTEM_STOPWORDS]
	if not tokens:
		return ''
	# First two meaningful tokens often identify a DS family.
	return '_'.join(tokens[:2])


def _slug(text: str) -> str:
	return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')
