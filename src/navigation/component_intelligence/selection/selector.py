"""Choose best foundation from synthesized cross-module guidance."""
from __future__ import annotations

import asyncio

from pathlib import Path

from ..contracts import IntelligenceContracts
from ..guidance.collectors import collect_guidance
from ..guidance.synthesis import rank_key
from ..integration_models import CandidateGuidance, FoundationSelection
from ..models import ComponentCandidate, ParsedQuery
from .filter import filter_candidates


async def select_foundation(
	candidates: list[ComponentCandidate],
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
	max_candidates: int = 12,
	contracts: IntelligenceContracts | None = None,
) -> FoundationSelection:
	shortlist = filter_candidates(
		candidates,
		max_count=max_candidates,
		page_context=(parsed_query.page_context if parsed_query else None),
	)
	if not shortlist:
		raise ValueError('no_candidates_after_filter')

	guided: list[tuple[ComponentCandidate, CandidateGuidance]] = []
	degraded: list[str] = []
	guidance_tasks = [
		collect_guidance(
			candidate,
			repo_root=repo_root,
			parsed_query=parsed_query,
			contracts=contracts,
		)
		for candidate in shortlist[:3]
	]
	guidance_results = await asyncio.gather(*guidance_tasks, return_exceptions=True)
	for candidate, result in zip(shortlist[:3], guidance_results, strict=True):
		if isinstance(result, BaseException):
			degraded.append(f'guidance_error:{candidate.id}')
			continue
		guided.append((candidate, result))
		for layer in (result.framework, result.codebase, result.design_sense, result.consistency):
			degraded.extend(layer.degraded)

	eligible = [(c, g) for c, g in guided if g.synthesis.eligible]
	if not eligible:
		eligible = guided

	eligible.sort(key=lambda pair: rank_key(pair[0], pair[1]))
	chosen, best_guidance = eligible[0]
	runner_ups = [c for c, _ in eligible[1:4]]
	rationale = _build_rationale(chosen, best_guidance)
	return FoundationSelection(
		chosen=chosen,
		guidance=best_guidance,
		runner_ups=runner_ups,
		rationale=rationale,
		degraded=list(dict.fromkeys(degraded)),
	)


def _build_rationale(candidate: ComponentCandidate, guidance: CandidateGuidance) -> str:
	return (
		f'Best foundation: {candidate.title}. '
		f'{guidance.synthesis.summary}. '
		f'Search relevance {candidate.relevance_score:.2f}.'
	)
