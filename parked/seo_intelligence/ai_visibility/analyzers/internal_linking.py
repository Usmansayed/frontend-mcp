"""AI internal linking — do pages link to each other so AI systems can discover them?

Source: Google's internal linking guidance
(https://developers.google.com/search/docs/crawling-indexing/links-crawlable).
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	evidence_by_kind,
	matches_any_phrase,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'internal_link', 'crawl_issue', 'technical_issue'}
_WEAK_PHRASES = ('orphan', 'broken link', 'no internal link', 'few internal links', 'thin internal linking', 'link-text', 'links do not have descriptive text')
_LINK_URL = 'https://developers.google.com/search/docs/crawling-indexing/links-crawlable'


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_internal_linking',
			status='skipped',
			score=0.0,
			rationale='No internal link evidence available.',
			rationale_url=_LINK_URL,
		)

	link_evidence = [e for e in relevant if e.kind.value == 'internal_link']
	weak_hits = [e for e in relevant if matches_any_phrase(e, _WEAK_PHRASES)]

	if weak_hits:
		return AiAnalyzerResult(
			analyzer_id='ai_internal_linking',
			status='warn',
			score=0.55,
			source_evidence_ids=[e.evidence_id for e in weak_hits],
			page_url=primary_page_url(weak_hits, base_url),
			title='Internal linking gaps',
			summary='Orphan pages, broken internal links, or non-descriptive anchor text detected. AI systems traverse links to discover related content.',
			severity='medium',
			rationale='Google linking guide: internal links help discovery; descriptive anchor text improves AI understanding of link targets.',
			rationale_url=_LINK_URL,
		)

	if link_evidence:
		return AiAnalyzerResult(
			analyzer_id='ai_internal_linking',
			status='pass',
			score=0.8,
			source_evidence_ids=[e.evidence_id for e in link_evidence[:5]],
			title='Internal linking healthy',
			summary=f'{len(link_evidence)} internal-link evidence item(s) present with no reported orphan/broken issues.',
			severity='info',
			rationale='Healthy internal linking helps AI systems discover and rank supporting pages.',
			rationale_url=_LINK_URL,
		)

	return AiAnalyzerResult(
		analyzer_id='ai_internal_linking',
		status='skipped',
		score=0.0,
		rationale='Link-related evidence exists but did not match orphan/broken patterns.',
		rationale_url=_LINK_URL,
	)
