"""Verification loop — analyze → recommend → apply → verify → repeat."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoRecommendation, SeoVerificationStatus


def build_verification_plan(recommendations: list[SeoRecommendation]) -> dict[str, object]:
	steps = []
	for rec in recommendations:
		steps.append({
			'recommendation_id': rec.recommendation_id,
			'status': SeoVerificationStatus.PENDING.value,
			'steps': list(rec.verification_steps) or [
				'Apply recommended fix in codebase',
				'perception_observe affected URL',
				'perception_verify expected outcome',
			],
		})
	return {
		'loop': 'analyze_recommend_apply_verify_repeat',
		'pending_count': len(steps),
		'items': steps,
	}
