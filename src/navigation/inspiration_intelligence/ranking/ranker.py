"""Candidate ranking — uses CandidateProfile metadata, not keywords alone."""
from __future__ import annotations

from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationIntent,
	InspirationRankedCandidate,
)


def rank_candidates(
	candidates: list[InspirationCandidate],
	*,
	intent: InspirationIntent,
	hints: dict[str, object],
	community_plan: CommunitySearchPlan | None = None,
) -> list[InspirationRankedCandidate]:
	ranked: list[InspirationRankedCandidate] = []
	stack = str(hints.get('component_stack') or '').lower()
	plan = community_plan

	for candidate in candidates:
		profile = candidate.profile
		score = max(candidate.discovery_score, profile.confidence * 0.5)
		rationale_parts: list[str] = []

		likes = candidate.metadata.get('likes')
		if isinstance(likes, int) and likes > 0:
			score += min(0.1, likes / 50_000)
			rationale_parts.append(f'likes:{likes}')

		if stack and profile.framework and stack in profile.framework.lower():
			score += 0.12
			rationale_parts.append(f'framework:{profile.framework}')

		for industry in plan.industries if plan else []:
			if industry in profile.industry:
				score += 0.1
				rationale_parts.append(f'industry:{industry}')

		for page in plan.page_types if plan else intent.target_styles:
			if page in profile.page_type:
				score += 0.1
				rationale_parts.append(f'page:{page}')

		for style in plan.styles if plan else intent.target_styles:
			if style in profile.style:
				score += 0.08
				rationale_parts.append(f'style:{style}')

		for lang in plan.design_languages if plan else []:
			if lang in profile.design_language:
				score += 0.08
				rationale_parts.append(f'language:{lang}')

		if profile.patterns:
			score += min(0.1, 0.03 * len(profile.patterns))
			rationale_parts.append(f'patterns:{len(profile.patterns)}')

		ranked.append(
			InspirationRankedCandidate(
				candidate=candidate,
				overall_score=min(1.0, score),
				rationale='; '.join(rationale_parts) or 'profile_confidence',
			)
		)

	ranked.sort(key=lambda item: item.overall_score, reverse=True)
	return ranked
