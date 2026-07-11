"""Recommendation engine — evidence-linked SEO fixes only."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation


def build_recommendations(
	evidence: list[SeoEvidenceRef],
	cross_analysis: list[dict[str, object]],
) -> list[SeoRecommendation]:
	if not evidence and not cross_analysis:
		return []

	recommendations: list[SeoRecommendation] = []

	for idx, analysis in enumerate(cross_analysis):
		evidence_ids = list(analysis.get('evidence_ids') or [])
		if not evidence_ids:
			continue
		recommendations.append(
			SeoRecommendation(
				recommendation_id=str(analysis.get('analysis_id') or f'cross_{idx}'),
				title=str(analysis.get('title') or 'Cross-source finding'),
				summary=str(analysis.get('summary') or ''),
				priority='medium',
				category='cross_analysis',
				evidence_ids=evidence_ids,
				confidence=float(analysis.get('confidence') or 0.5),
				verification_steps=[
					'Re-run perception_observe on affected URLs',
					'Compare Search Console index status after fix',
					'Re-run Lighthouse on landing pages',
				],
			)
		)

	for item in evidence:
		if item.severity not in ('high', 'critical'):
			continue
		recommendations.append(
			SeoRecommendation(
				recommendation_id=f'rec_{item.evidence_id}',
				title=f'Address: {item.title}',
				summary=item.summary,
				priority='high' if item.severity == 'critical' else 'medium',
				category=item.kind.value,
				evidence_ids=[item.evidence_id],
				confidence=0.7,
				verification_steps=['Verify fix with perception_verify after code change'],
			)
		)

	return recommendations
