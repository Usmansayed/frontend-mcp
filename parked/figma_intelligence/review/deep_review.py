"""Deep Candidate Review — score extracted design, not metadata alone."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.figma_intelligence.adapters.ecosystem import (
	score_consistency_fit,
	score_component_reuse,
	score_design_quality,
	score_framework_fit,
	score_extraction_design_quality,
	score_extraction_consistency,
	score_extraction_component_reuse,
	score_extraction_framework_fit,
)
from navigation.figma_intelligence.models import FigmaExtractionResult, FigmaIntent, FigmaRankedCandidate


@dataclass(slots=True)
class DeepReviewResult:
	"""Post-extraction multi-intelligence scores."""

	candidate_id: str
	provider_id: str
	design_quality_score: float = 0.0
	consistency_fit: float = 0.0
	component_reuse_score: float = 0.0
	framework_fit: float = 0.0
	inspiration_score: float = 0.0
	overall_score: float = 0.0
	metadata_weight: float = 0.0
	extraction_weight: float = 0.0
	rationale: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate_id': self.candidate_id,
			'provider_id': self.provider_id,
			'design_quality_score': self.design_quality_score,
			'consistency_fit': self.consistency_fit,
			'component_reuse_score': self.component_reuse_score,
			'framework_fit': self.framework_fit,
			'inspiration_score': self.inspiration_score,
			'overall_score': self.overall_score,
			'metadata_weight': self.metadata_weight,
			'extraction_weight': self.extraction_weight,
			'rationale': self.rationale,
			'degraded': list(self.degraded),
		}


def deep_review_extractions(
	extractions: list[FigmaExtractionResult],
	*,
	ranked_by_id: dict[str, FigmaRankedCandidate],
	intent: FigmaIntent,
	repo_root: str,
) -> tuple[list[DeepReviewResult], list[str]]:
	"""Score actual extracted tokens/components — not profile metadata alone."""
	degraded: list[str] = []
	if not repo_root:
		degraded.append('deep_review_without_repo_root')

	results: list[DeepReviewResult] = []
	for extraction in extractions:
		ranked = ranked_by_id.get(extraction.candidate_id)
		candidate = ranked.candidate if ranked else None

		# Metadata lane (pre-extraction profile).
		meta_dq = meta_cf = meta_cr = meta_ff = 0.0
		meta_deg: list[str] = []
		if candidate is not None:
			meta_dq, d1 = score_design_quality(candidate, repo_root=repo_root)
			meta_cf, d2 = score_consistency_fit(candidate, repo_root=repo_root)
			meta_cr, d3 = score_component_reuse(candidate, repo_root=repo_root)
			meta_ff, d4 = score_framework_fit(candidate, repo_root=repo_root)
			meta_deg = d1 + d2 + d3 + d4

		# Extraction lane (actual design data).
		ext_dq, e1 = score_extraction_design_quality(extraction, repo_root=repo_root)
		ext_cf, e2 = score_extraction_consistency(extraction, repo_root=repo_root)
		ext_cr, e3 = score_extraction_component_reuse(extraction, repo_root=repo_root)
		ext_ff, e4 = score_extraction_framework_fit(extraction, repo_root=repo_root)
		ext_deg = e1 + e2 + e3 + e4

		degraded.extend(meta_deg + ext_deg)

		has_extraction = bool(extraction.tokens or extraction.components or extraction.variables)
		meta_weight = 0.35 if has_extraction else 1.0
		ext_weight = 0.65 if has_extraction else 0.0

		design_quality = meta_weight * meta_dq + ext_weight * ext_dq
		consistency = meta_weight * meta_cf + ext_weight * ext_cf
		component_reuse = meta_weight * meta_cr + ext_weight * ext_cr
		framework = meta_weight * meta_ff + ext_weight * ext_ff
		inspiration = (design_quality + consistency + component_reuse + framework) / 4.0
		overall = inspiration

		parts: list[str] = []
		if has_extraction:
			parts.append(f'tokens:{len(extraction.tokens)}')
			parts.append(f'components:{len(extraction.components)}')
		if ranked:
			parts.append(f'rank:{ranked.overall_score:.2f}')

		results.append(
			DeepReviewResult(
				candidate_id=extraction.candidate_id,
				provider_id=extraction.provider_id,
				design_quality_score=design_quality,
				consistency_fit=consistency,
				component_reuse_score=component_reuse,
				framework_fit=framework,
				inspiration_score=inspiration,
				overall_score=overall,
				metadata_weight=meta_weight,
				extraction_weight=ext_weight,
				rationale='; '.join(parts) or 'deep_review',
				degraded=ext_deg if not has_extraction else [],
			)
		)

	results.sort(key=lambda r: r.overall_score, reverse=True)
	return results, degraded
