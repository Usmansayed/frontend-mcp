"""Multi-intelligence evaluation — post-extraction and pre-extraction ranking."""
from __future__ import annotations

from navigation.figma_intelligence.adapters.ecosystem import (
	score_consistency_fit,
	score_design_quality,
	score_framework_fit,
	score_component_reuse,
)
from navigation.figma_intelligence.models import FigmaIntent, FigmaRankedCandidate


def evaluate_candidates(
	candidates: list[FigmaRankedCandidate],
	*,
	intent: FigmaIntent,
	repo_root: str,
) -> tuple[list[FigmaRankedCandidate], list[str]]:
	degraded: list[str] = []
	if not repo_root:
		degraded.append('evaluation_without_repo_root')

	evaluated: list[FigmaRankedCandidate] = []
	for item in candidates:
		dq, dq_deg = score_design_quality(item.candidate, repo_root=repo_root)
		cf, cf_deg = score_consistency_fit(item.candidate, repo_root=repo_root)
		cr, cr_deg = score_component_reuse(item.candidate, repo_root=repo_root)
		ff, ff_deg = score_framework_fit(item.candidate, repo_root=repo_root)
		degraded.extend(dq_deg + cf_deg + cr_deg + ff_deg)

		inspiration = (dq + cf + cr + ff) / 4.0 if any([dq, cf, cr, ff]) else item.overall_score
		overall = 0.35 * item.overall_score + 0.65 * inspiration

		evaluated.append(
			FigmaRankedCandidate(
				candidate=item.candidate,
				inspiration_score=inspiration,
				consistency_fit=cf,
				component_reuse_score=cr,
				design_quality_score=dq,
				framework_fit=ff,
				overall_score=overall,
				rationale=item.rationale,
				degraded=list(item.degraded),
			)
		)

	evaluated.sort(key=lambda x: x.overall_score, reverse=True)
	return evaluated, degraded
