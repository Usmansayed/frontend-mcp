"""AI readiness correlation detection — mirrors development_practices.py pattern.

Consumes the full evidence list (upstream + AI-derived) and emits correlation
dicts consumed by the existing recommendation pipeline. Every correlation
cites the upstream + derived evidence IDs used to produce it.
"""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.models import SeoEvidenceRef

_ANALYZER_TO_TITLE: dict[str, tuple[str, str, str]] = {
	'ai_crawlability': (
		'AI readiness: crawlability',
		'Fix indexing or crawl blockers so AI features (which reuse the search index) can reach your content.',
		'high',
	),
	'ai_extractability': (
		'AI readiness: extractability',
		'Ensure the main content renders without JS or hydration errors and meets Core Web Vitals so AI systems can parse it.',
		'high',
	),
	'ai_citation_readiness': (
		'AI readiness: citation metadata',
		'Add unique title, meta description, canonical, and Open Graph tags so AI features can construct clean citations.',
		'high',
	),
	'ai_entity_coverage': (
		'AI readiness: entity coverage',
		'Add valid Schema.org JSON-LD (Organization, WebSite, primary content type) — standard vocabulary only, no "AI-specific" types.',
		'medium',
	),
	'ai_schema_quality': (
		'AI readiness: fix structured data errors',
		'Repair invalid or malformed JSON-LD so rich-results and AI systems can parse the markup.',
		'high',
	),
	'ai_semantic_html': (
		'AI readiness: semantic HTML',
		'Use one logical H1, ordered H2/H3, and a valid lang attribute so extractors can navigate the page.',
		'medium',
	),
	'ai_trust_signals': (
		'AI readiness: publisher identity',
		'Add Organization schema with sameAs (LinkedIn, GitHub, X, etc.) so AI systems can attribute content correctly.',
		'medium',
	),
	'ai_internal_linking': (
		'AI readiness: internal linking',
		'Add descriptive internal links between related pages so AI systems can discover supporting content.',
		'medium',
	),
	'ai_content_structure': (
		'AI readiness: content structure',
		'Break long text into sections with H2/H3 and lists — do not use artificial "chunking".',
		'low',
	),
	'ai_faq_answer_blocks': (
		'AI readiness: visible Q&A blocks',
		'Prefer visible, heading-based Q&A. FAQ rich results were retired in May 2026 — do not rely on FAQPage JSON-LD.',
		'low',
	),
	'ai_crawler_access': (
		'AI crawler access rules',
		'Observed AI-crawler rules in robots.txt. Whether to allow them is a policy choice — reporting for visibility only.',
		'info',
	),
	'ai_llms_txt_optional': (
		'llms.txt observed',
		'Informational only — Google\'s guidance says llms.txt is not needed for AI features.',
		'info',
	),
}


def detect_ai_readiness(
	evidence: list[SeoEvidenceRef],
	*,
	base_url: str = '',
) -> list[dict[str, object]]:
	"""One correlation per derived AI evidence item with a title/fix mapping."""
	ai_evidence = [e for e in evidence if e.kind.value == 'ai_visibility']
	if not ai_evidence:
		return []

	correlations: list[dict[str, object]] = []
	for item in ai_evidence:
		analyzer_id = str((item.metadata or {}).get('analyzer_id') or '')
		if analyzer_id not in _ANALYZER_TO_TITLE:
			continue
		status = str((item.metadata or {}).get('status') or 'warn')
		if status in {'pass', 'skipped'}:
			continue

		title, fix_guidance, default_priority = _ANALYZER_TO_TITLE[analyzer_id]
		priority = _priority_for(status, default_priority)
		source_ids = list((item.metadata or {}).get('source_evidence_ids') or [])
		evidence_ids = [item.evidence_id, *source_ids]

		correlations.append({
			'analysis_id': f'ai_readiness_{analyzer_id.removeprefix("ai_")}',
			'scope': 'page' if item.page_url else 'site',
			'page_url': normalize_page_url(item.page_url, base_url=base_url) if item.page_url else '',
			'title': title,
			'summary': item.summary or (item.metadata or {}).get('rationale') or fix_guidance,
			'root_cause': (item.metadata or {}).get('rationale') or item.summary or '',
			'business_impact': 'Improves visibility and citation quality in Google AI Overviews and other AI answer systems.',
			'category': 'ai_visibility',
			'priority': priority,
			'evidence_ids': evidence_ids,
			'confidence': _confidence_for(status),
			'metadata': {
				'analyzer_id': analyzer_id,
				'status': status,
				'score': (item.metadata or {}).get('score'),
				'rationale_url': (item.metadata or {}).get('rationale_url'),
			},
		})
	return correlations


def _priority_for(status: str, default: str) -> str:
	if status == 'fail':
		return 'high' if default != 'info' else 'medium'
	if status == 'warn':
		return default if default in {'high', 'medium'} else 'medium'
	return default


def _confidence_for(status: str) -> float:
	if status == 'fail':
		return 0.85
	if status == 'warn':
		return 0.65
	return 0.5
