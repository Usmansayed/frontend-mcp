"""Recommendation engine — evidence-linked SEO fixes only."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation

_FIX_GUIDANCE: dict[str, str] = {
	'indexing_rendering_correlation': 'Ensure critical content is server-rendered or pre-rendered; fix hydration errors before requesting recrawl.',
	'cwv_rendering_correlation': 'Reduce JS bundle size, defer non-critical scripts, fix layout shifts and long tasks.',
	'ctr_cwv_correlation': 'Improve LCP/CLS on high-impression landing pages; re-test with Lighthouse after deploy.',
	'technical_index_correlation': 'Fix canonicals, redirects, and robots rules surfaced by technical crawl.',
	'broken_pages_with_search_visibility': 'Return 200 for important URLs or redirect with 301; remove from sitemap if intentionally gone.',
	'traffic_query_landing_alignment': 'Map top queries to landing pages in GA4 and GSC; consolidate thin duplicates.',
}


def build_recommendations(
	evidence: list[SeoEvidenceRef],
	cross_analysis: list[dict[str, object]],
) -> list[SeoRecommendation]:
	if not evidence and not cross_analysis:
		return []

	recommendations: list[SeoRecommendation] = []
	seen_ids: set[str] = set()

	for idx, analysis in enumerate(cross_analysis):
		evidence_ids = list(analysis.get('evidence_ids') or [])
		if not evidence_ids:
			continue
		analysis_id = str(analysis.get('analysis_id') or f'cross_{idx}')
		if analysis_id in seen_ids:
			continue
		seen_ids.add(analysis_id)
		confidence = float(analysis.get('confidence') or 0.5)
		recommendations.append(
			SeoRecommendation(
				recommendation_id=analysis_id,
				title=str(analysis.get('title') or 'Cross-source finding'),
				summary=str(analysis.get('summary') or ''),
				priority='high' if confidence >= 0.65 else 'medium',
				category='cross_analysis',
				evidence_ids=evidence_ids,
				confidence=confidence,
				fix_guidance=_FIX_GUIDANCE.get(analysis_id, ''),
				verification_steps=[
					'Apply fix in codebase or CMS',
					'perception_observe affected URLs (save scan_id)',
					'perception_seo_verify with recommendation_ids',
					'perception_verify UI expectations',
				],
			)
		)

	evidence_by_id = {item.evidence_id: item for item in evidence}
	for item in evidence:
		if item.severity not in ('high', 'critical'):
			continue
		rec_id = f'rec_{item.evidence_id}'
		if rec_id in seen_ids:
			continue
		seen_ids.add(rec_id)
		recommendations.append(
			SeoRecommendation(
				recommendation_id=rec_id,
				title=f'Address: {item.title}',
				summary=item.summary,
				priority='high' if item.severity == 'critical' else 'medium',
				category=item.kind.value,
				evidence_ids=[item.evidence_id],
				confidence=0.75,
				fix_guidance=_fix_guidance_for_evidence(item),
				verification_steps=[
					'Apply recommended fix',
					'perception_observe affected URL',
					'perception_seo_verify',
					'perception_verify expected outcome',
				],
			)
		)

	# Boost recommendations backed by multiple high-severity evidence items
	for rec in recommendations:
		if rec.category != 'cross_analysis':
			continue
		related = [evidence_by_id[eid] for eid in rec.evidence_ids if eid in evidence_by_id]
		high_count = sum(1 for e in related if e.severity in {'high', 'critical'})
		if high_count >= 2:
			rec.priority = 'high'
			rec.confidence = min(0.95, rec.confidence + 0.1)

	return recommendations


def _fix_guidance_for_evidence(item: SeoEvidenceRef) -> str:
	kind = item.kind.value
	if kind == 'rendering_issue':
		return 'Fix console errors and blocking dev insights; verify client render matches server HTML.'
	if kind == 'core_web_vital':
		return 'Optimize LCP element, reduce CLS from dynamic content, improve main-thread responsiveness.'
	if kind in {'crawl_issue', 'technical_issue'}:
		return 'Resolve crawl/HTTP/canonical issue and re-run technical crawl.'
	if kind == 'index_status':
		return 'Fix coverage blockers; request indexing in Search Console after deploy.'
	return ''
