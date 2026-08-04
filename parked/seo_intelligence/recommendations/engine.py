"""Recommendation engine — deterministic fallback; consumes reasoning_context_v2 units (ADR-027)."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.models import SeoEvidenceRef, SeoRecommendation

_FIX_GUIDANCE: dict[str, str] = {
	'indexing_rendering_correlation': 'Ensure critical content is server-rendered or pre-rendered; fix hydration errors before requesting recrawl.',
	'cwv_rendering_correlation': 'Reduce JS bundle size, defer non-critical scripts, fix layout shifts and long tasks.',
	'ctr_cwv_correlation': 'Improve LCP/CLS on high-impression landing pages; re-test with Lighthouse after deploy.',
	'technical_index_correlation': 'Fix canonicals, redirects, and robots rules surfaced by technical crawl.',
	'broken_pages_with_search_visibility': 'Return 200 for important URLs or redirect with 301; remove from sitemap if intentionally gone.',
	'traffic_query_landing_alignment': 'Map top queries to landing pages in GA4 and GSC; consolidate thin duplicates.',
	'opportunity_weak_metadata': 'Add unique title and meta description per page; expand thin content where queries show demand.',
	'opportunity_internal_links': 'Add contextual internal links from hub pages to striking-distance URLs.',
	'opportunity_indexing': 'Resolve coverage blockers, fix canonicals, then request indexing in Search Console.',
	'opportunity_cwv_quick_win': 'Optimize LCP element, reduce CLS, defer non-critical JS; verify with Lighthouse.',
	'dev_practice_metadata': 'Add unique title and meta description per page; set canonical URLs.',
	'dev_practice_schema': 'Add valid JSON-LD for primary page type (Organization, WebSite, Article, etc.).',
	'dev_practice_accessibility_cwv': 'Fix Lighthouse accessibility audits and CWV metrics before launch.',
	'dev_practice_rendering': 'Fix hydration/console errors; verify server HTML matches client render.',
	'dev_practice_internal_links': 'Add contextual internal links from hub pages to key content.',
	'dev_practice_semantic_html': 'Use one H1 per page, logical heading order, and descriptive alt text on images.',
	'ai_readiness_crawlability': 'Ensure the page is indexed in Search Console; publish robots.txt and sitemap.xml; return 2xx for canonical URLs.',
	'ai_readiness_extractability': 'Server-render main content or verify JS execution; fix hydration errors; meet LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms.',
	'ai_readiness_citation_readiness': 'Add unique <title>, meta description, rel=canonical, Open Graph (og:title/description/image), and Twitter Card tags.',
	'ai_readiness_entity_coverage': 'Add standard Schema.org JSON-LD (Organization, WebSite, and the page\'s primary type). No AI-specific schema types exist.',
	'ai_readiness_schema_quality': 'Fix JSON-LD syntax and required-field errors reported by the crawl; verify with Schema.org validator and Google rich-results test.',
	'ai_readiness_semantic_html': 'Use exactly one H1 per page, logical H2/H3 order, and a valid <html lang="..."> attribute.',
	'ai_readiness_trust_signals': 'Publish Organization schema with sameAs links to canonical profiles (LinkedIn, GitHub, X). Never fabricate credentials.',
	'ai_readiness_internal_linking': 'Add descriptive, contextual internal links between related pages. Avoid generic anchor text like "click here".',
	'ai_readiness_content_structure': 'Break long content into sections with H2/H3 and lists; do not use artificial chunking.',
	'ai_readiness_faq_answer_blocks': 'Add visible, heading-based Q&A sections. Do not rely on FAQPage JSON-LD (rich results retired May 2026).',
	'ai_readiness_crawler_access': 'Review AI crawler rules in robots.txt (GPTBot, ClaudeBot, PerplexityBot). Allowing or blocking is a policy choice — no fix required.',
	'ai_readiness_llms_txt_optional': 'Informational only — Google\'s guidance says llms.txt is not required for AI features.',
}

_BUSINESS_IMPACT: dict[str, str] = {
	'indexing_rendering_correlation': 'Unindexed pages lose all organic traffic for affected URLs',
	'cwv_rendering_correlation': 'Poor page experience hurts rankings and conversion on high-traffic pages',
	'ctr_cwv_correlation': 'CTR gains on high-impression queries increase traffic without new rankings',
	'technical_index_correlation': 'Technical blockers prevent Google from indexing valuable content',
	'broken_pages_with_search_visibility': 'Error pages waste crawl budget and erode user trust from SERPs',
	'traffic_query_landing_alignment': 'Misaligned landing pages leak conversion and confuse relevance signals',
	'ai_readiness_crawlability': 'Un-indexed pages cannot appear in AI Overviews or AI Mode citations',
	'ai_readiness_extractability': 'If AI systems cannot render your page, they cannot cite it',
	'ai_readiness_citation_readiness': 'Missing snippet metadata produces low-quality AI citations and link previews',
	'ai_readiness_entity_coverage': 'Ambiguous entities are less likely to be attributed correctly by AI systems',
	'ai_readiness_schema_quality': 'Invalid JSON-LD disqualifies rich results and confuses entity extraction',
	'ai_readiness_semantic_html': 'Poor heading structure hurts both accessibility and AI extraction',
	'ai_readiness_trust_signals': 'Weak identity signals reduce E-E-A-T alignment and AI attribution accuracy',
	'ai_readiness_internal_linking': 'Weak internal linking limits discovery of supporting pages by AI crawlers',
	'ai_readiness_content_structure': 'Wall-of-text pages are harder for AI systems to summarize or excerpt',
}

_DEFAULT_VERIFICATION = [
	'Apply fix in codebase or CMS',
	'perception_observe affected URLs (save scan_id)',
	'perception_seo_verify with recommendation_ids',
	'perception_verify UI and metadata expectations',
]


def build_recommendations(
	evidence: list[SeoEvidenceRef],
	correlations: list[dict[str, object]],
	*,
	reasoning_units: list[dict[str, Any]] | None = None,
) -> list[SeoRecommendation]:
	if not evidence and not correlations:
		return []

	unit_by_corr: dict[str, dict[str, Any]] = {}
	for unit in reasoning_units or []:
		corr_id = str(unit.get('correlation_id') or '')
		if corr_id:
			unit_by_corr[corr_id] = unit

	recommendations: list[SeoRecommendation] = []
	seen_ids: set[str] = set()
	evidence_by_id = {item.evidence_id: item for item in evidence}

	for idx, analysis in enumerate(correlations):
		evidence_ids = list(analysis.get('evidence_ids') or [])
		if not evidence_ids:
			continue
		analysis_id = str(analysis.get('analysis_id') or f'cross_{idx}')
		if analysis_id in seen_ids:
			continue
		seen_ids.add(analysis_id)

		unit = unit_by_corr.get(analysis_id, {})
		confidence_block = unit.get('confidence') or {}
		confidence = float(confidence_block.get('score') or analysis.get('confidence') or 0.5)
		impact = unit.get('impact') or {}
		priority = str(analysis.get('priority') or _priority_from_unit(unit, confidence))

		recommendations.append(
			SeoRecommendation(
				recommendation_id=analysis_id,
				title=str(analysis.get('title') or 'Cross-source finding'),
				summary=str(analysis.get('summary') or ''),
				root_cause=str(analysis.get('root_cause') or analysis.get('summary') or ''),
				business_impact=str(
					analysis.get('business_impact') or _BUSINESS_IMPACT.get(analysis_id, 'Improves organic visibility and traffic quality')
				),
				priority=priority,
				category=str(analysis.get('category') or 'cross_analysis'),
				evidence_ids=evidence_ids,
				confidence=confidence,
				fix_guidance=_FIX_GUIDANCE.get(analysis_id, ''),
				verification_steps=list(_DEFAULT_VERIFICATION),
				metadata={
					'page_url': analysis.get('page_url') or '',
					'confidence_composition': confidence_block.get('composition'),
					'impact': impact,
					'reasoning_unit_id': unit.get('unit_id'),
					'codebase_hints': unit.get('codebase_hints') or [],
				},
			)
		)

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
				root_cause=item.summary,
				business_impact=_business_impact_for_evidence(item),
				priority='high' if item.severity == 'critical' else 'medium',
				category=item.kind.value,
				evidence_ids=[item.evidence_id],
				confidence=0.75,
				fix_guidance=_fix_guidance_for_evidence(item),
				verification_steps=list(_DEFAULT_VERIFICATION),
				metadata={'page_url': item.page_url or item.url},
			)
		)

	recommendations.sort(
		key=lambda r: (
			-_priority_score(r.priority),
			-float((r.metadata or {}).get('impact', {}).get('score', 0)),
			-r.confidence,
		)
	)
	return recommendations


def _priority_from_unit(unit: dict[str, Any], confidence: float) -> str:
	impact_score = float((unit.get('impact') or {}).get('score', 0))
	if impact_score >= 0.7 or confidence >= 0.8:
		return 'high'
	if impact_score >= 0.4 or confidence >= 0.6:
		return 'medium'
	return 'low'


def _priority_score(priority: str) -> int:
	return {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(priority, 2)


def _business_impact_for_evidence(item: SeoEvidenceRef) -> str:
	kind = item.kind.value
	if kind == 'rendering_issue':
		return 'Broken rendering can block indexing and hurt conversions'
	if kind == 'core_web_vital':
		return 'Page experience signals affect rankings and user engagement'
	if kind in {'crawl_issue', 'technical_issue'}:
		return 'Technical errors waste crawl budget and block indexation'
	if kind == 'index_status':
		return 'Index coverage gaps directly reduce organic reach'
	return 'Resolving this issue improves organic search performance'


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
