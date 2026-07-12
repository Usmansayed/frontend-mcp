"""AI citation readiness — does the page provide the metadata AI systems use to cite?

Sources:
- Google snippet guide (https://developers.google.com/search/docs/appearance/snippet)
- Google canonicalization guide (https://developers.google.com/search/docs/crawling-indexing/canonicalization)
Rationale: AI features often cite pages the way snippets appear. Missing
canonical / meta description / Open Graph fields reduces the quality of any
citation Google's AI features can construct.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	matches_any_phrase,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'technical_issue', 'crawl_issue', 'index_status'}

_META_PHRASES = ('meta description', 'meta-description')
_CANONICAL_PHRASES = ('canonical',)
_OG_PHRASES = ('open graph', 'og:', 'og image', 'og description', 'ogp')
_TWITTER_PHRASES = ('twitter card', 'twitter:card', 'twitter card tags')
_TITLE_PHRASES = ('document title', '<title>', 'page title')


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_citation_readiness',
			status='skipped',
			score=0.0,
			rationale='No technical/crawl/index_status evidence to inspect for citation metadata.',
			rationale_url=ai_guide_url(),
		)

	buckets: dict[str, list[SeoEvidenceRef]] = {}
	for item in relevant:
		if matches_any_phrase(item, _META_PHRASES):
			buckets.setdefault('meta_description', []).append(item)
		if matches_any_phrase(item, _CANONICAL_PHRASES):
			buckets.setdefault('canonical', []).append(item)
		if matches_any_phrase(item, _OG_PHRASES):
			buckets.setdefault('open_graph', []).append(item)
		if matches_any_phrase(item, _TWITTER_PHRASES):
			buckets.setdefault('twitter_card', []).append(item)
		if matches_any_phrase(item, _TITLE_PHRASES):
			buckets.setdefault('title', []).append(item)

	if not buckets:
		return AiAnalyzerResult(
			analyzer_id='ai_citation_readiness',
			status='pass',
			score=0.9,
			source_evidence_ids=[e.evidence_id for e in relevant],
			title='Citation metadata looks healthy',
			summary='No crawl or Lighthouse issues found for title, description, canonical, or social preview tags.',
			severity='info',
			rationale='Snippet-eligible metadata is Google\'s prerequisite for AI Overview citations.',
			rationale_url='https://developers.google.com/search/docs/appearance/snippet',
		)

	missing = sorted(buckets.keys())
	sample_ids: list[str] = []
	for items in buckets.values():
		sample_ids.extend(e.evidence_id for e in items[:2])
	priority_missing = {'meta_description', 'canonical', 'title'}
	is_high = bool(priority_missing.intersection(missing))
	score = max(0.15, 1.0 - 0.2 * len(missing))
	page_url = primary_page_url(sum(buckets.values(), []), base_url)
	return AiAnalyzerResult(
		analyzer_id='ai_citation_readiness',
		status='fail' if is_high else 'warn',
		score=score,
		source_evidence_ids=sample_ids,
		page_url=page_url,
		title='Citation metadata gaps',
		summary=f'Missing or weak citation metadata: {", ".join(missing)}.',
		severity='high' if is_high else 'medium',
		rationale='Google snippet guide: unique title, meta description, and canonical are required to be snippet-eligible; Open Graph/Twitter tags improve link previews and citations.',
		rationale_url='https://developers.google.com/search/docs/appearance/snippet',
		metadata={'missing_fields': missing},
	)
