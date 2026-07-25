"""AI semantic HTML — proper heading order, lang attribute, structural markup.

Sources:
- WCAG 2.1 Section headings 2.4.10 (https://www.w3.org/WAI/WCAG21/Understanding/section-headings.html)
- MDN semantic HTML guide
Semantic HTML helps both accessibility and machine extraction (including AI
retrieval systems that parse the DOM).
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	evidence_by_kind,
	matches_any_phrase,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'technical_issue', 'crawl_issue', 'rendering_issue'}
_PHRASES = (
	'heading-order',
	'hierarchical-headings',
	'multiple h1',
	'no h1',
	'missing h1',
	'html-has-lang',
	'lang attribute',
	'landmark',
	'main landmark',
	'skipped heading',
)
_SOURCE_URL = 'https://www.w3.org/WAI/WCAG21/Understanding/section-headings.html'


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_semantic_html',
			status='skipped',
			score=0.0,
			rationale='No technical/rendering evidence to inspect for semantic HTML issues.',
			rationale_url=_SOURCE_URL,
		)

	hits = [e for e in relevant if matches_any_phrase(e, _PHRASES)]
	if not hits:
		return AiAnalyzerResult(
			analyzer_id='ai_semantic_html',
			status='pass',
			score=0.85,
			source_evidence_ids=[e.evidence_id for e in relevant[:5]],
			title='Semantic HTML looks healthy',
			summary='No heading-order, H1, or lang-attribute issues detected in current evidence.',
			severity='info',
			rationale='Well-structured semantic HTML makes content easier for AI systems to extract.',
			rationale_url=_SOURCE_URL,
		)

	return AiAnalyzerResult(
		analyzer_id='ai_semantic_html',
		status='warn',
		score=0.55,
		source_evidence_ids=[e.evidence_id for e in hits],
		page_url=primary_page_url(hits, base_url),
		title='Semantic HTML gaps',
		summary='Heading order, H1 count, or lang attribute issues detected.',
		severity='medium',
		rationale='WCAG 2.4.10: use headings to organize content; a single logical H1 per page helps both humans and machines.',
		rationale_url=_SOURCE_URL,
		metadata={'hits': [h.title for h in hits[:5]]},
	)
