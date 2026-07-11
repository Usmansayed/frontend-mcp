"""Deep Candidate Review — score captured screenshots, not metadata alone."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.inspiration_intelligence.adapters.ecosystem import (
	score_capture_component_reuse,
	score_capture_consistency,
	score_capture_design_quality,
	score_capture_framework_fit,
	score_component_reuse,
	score_consistency_fit,
	score_design_quality,
	score_framework_fit,
)
from navigation.inspiration_intelligence.models import (
	InspirationCaptureResult,
	InspirationIntent,
	InspirationRankedCandidate,
)


@dataclass(slots=True)
class DeepReviewResult:
	"""Post-capture multi-intelligence scores."""

	candidate_id: str
	provider_id: str
	design_quality_score: float = 0.0
	consistency_fit: float = 0.0
	component_reuse_score: float = 0.0
	framework_fit: float = 0.0
	inspiration_score: float = 0.0
	overall_score: float = 0.0
	metadata_weight: float = 0.0
	capture_weight: float = 0.0
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
			'capture_weight': self.capture_weight,
			'rationale': self.rationale,
			'degraded': list(self.degraded),
		}


def deep_review_captures(
	captures: list[InspirationCaptureResult],
	*,
	ranked_by_id: dict[str, InspirationRankedCandidate],
	intent: InspirationIntent,
	repo_root: str,
) -> tuple[list[DeepReviewResult], list[str]]:
	"""Score actual captured screenshots — not profile metadata alone."""
	_ = intent
	degraded: list[str] = []
	if not repo_root:
		degraded.append('deep_review_without_repo_root')

	results: list[DeepReviewResult] = []
	for capture in captures:
		ranked = ranked_by_id.get(capture.candidate_id)
		candidate = ranked.candidate if ranked else None

		meta_dq = meta_cf = meta_cr = meta_ff = 0.0
		meta_deg: list[str] = []
		if candidate is not None:
			meta_dq, d1 = score_design_quality(candidate, repo_root=repo_root)
			meta_cf, d2 = score_consistency_fit(candidate, repo_root=repo_root)
			meta_cr, d3 = score_component_reuse(candidate, repo_root=repo_root)
			meta_ff, d4 = score_framework_fit(candidate, repo_root=repo_root)
			meta_deg = d1 + d2 + d3 + d4

		cap_dq, e1 = score_capture_design_quality(capture, repo_root=repo_root)
		cap_cf, e2 = score_capture_consistency(capture, repo_root=repo_root)
		cap_cr, e3 = score_capture_component_reuse(capture, repo_root=repo_root)
		cap_ff, e4 = score_capture_framework_fit(capture, repo_root=repo_root)
		cap_deg = e1 + e2 + e3 + e4

		degraded.extend(meta_deg + cap_deg)

		has_capture = bool(capture.screenshot_refs)
		meta_weight = 0.35 if has_capture else 1.0
		cap_weight = 0.65 if has_capture else 0.0

		design_quality = meta_weight * meta_dq + cap_weight * cap_dq
		consistency = meta_weight * meta_cf + cap_weight * cap_cf
		component_reuse = meta_weight * meta_cr + cap_weight * cap_cr
		framework = meta_weight * meta_ff + cap_weight * cap_ff
		inspiration = (design_quality + consistency + component_reuse + framework) / 4.0
		overall = inspiration

		parts: list[str] = []
		if has_capture:
			parts.append(f'screenshots:{len(capture.screenshot_refs)}')
			parts.append(f'patterns:{len(capture.patterns)}')
		if ranked:
			parts.append(f'rank:{ranked.overall_score:.2f}')

		results.append(
			DeepReviewResult(
				candidate_id=capture.candidate_id,
				provider_id=capture.provider_id,
				design_quality_score=design_quality,
				consistency_fit=consistency,
				component_reuse_score=component_reuse,
				framework_fit=framework,
				inspiration_score=inspiration,
				overall_score=overall,
				metadata_weight=meta_weight,
				capture_weight=cap_weight,
				rationale='; '.join(parts) or 'deep_review',
				degraded=cap_deg if not has_capture else [],
			)
		)

	results.sort(key=lambda r: r.overall_score, reverse=True)
	return results, degraded
