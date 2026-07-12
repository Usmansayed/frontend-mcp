"""AI crawlability — is the site indexable and crawlable?

Source: Google — Optimizing for generative AI features on Google Search
(https://developers.google.com/search/docs/fundamentals/ai-optimization-guide):
"a page must be indexed and eligible to be shown in Google Search with a
snippet."
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'index_status', 'crawl_issue', 'technical_issue'}
_INDEX_FAIL = {'FAIL', 'PARTIAL'}
_INDEX_PASS = {'PASS', 'NEUTRAL'}
_BLOCK_PHRASES = ('robots.txt', 'sitemap', 'not indexed', '404', '5xx', 'blocked')


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_crawlability',
			status='skipped',
			score=0.0,
			rationale='No index_status, crawl_issue or technical_issue evidence available.',
			rationale_url=ai_guide_url(),
		)

	index_evidence = [e for e in relevant if e.kind.value == 'index_status']
	blockers = [
		e for e in relevant
		if e.kind.value != 'index_status' and _looks_like_blocker(e)
	]

	verdicts = [_index_verdict(e) for e in index_evidence]
	failed_verdicts = [v for v in verdicts if v in _INDEX_FAIL]
	passed_verdicts = [v for v in verdicts if v in _INDEX_PASS]

	source_ids = [e.evidence_id for e in index_evidence + blockers]
	if failed_verdicts:
		return AiAnalyzerResult(
			analyzer_id='ai_crawlability',
			status='fail',
			score=0.1,
			source_evidence_ids=source_ids,
			page_url=primary_page_url(index_evidence or blockers, base_url),
			title='Page not eligible for AI Overviews (indexing blocked)',
			summary='Google Search Console reports the page is not indexed. Generative AI features reuse the search index, so an unindexed page cannot be cited.',
			severity='high',
			rationale='Google requires pages to be indexed and eligible to appear in Search with a snippet to be shown in AI features.',
			rationale_url=ai_guide_url(),
			metadata={'failed_verdicts': failed_verdicts},
		)

	if blockers:
		return AiAnalyzerResult(
			analyzer_id='ai_crawlability',
			status='warn',
			score=0.55,
			source_evidence_ids=source_ids,
			page_url=primary_page_url(blockers, base_url),
			title='Crawlability signals need attention',
			summary='Crawl blockers detected (robots.txt, sitemap, 4xx/5xx, or similar). Fix so AI systems can reliably reach and re-fetch the content.',
			severity='medium',
			rationale='Google guide: ensure your content is crawlable so AI systems and Search can reach it.',
			rationale_url=ai_guide_url(),
			metadata={'blocker_titles': [e.title for e in blockers[:5]]},
		)

	if passed_verdicts:
		return AiAnalyzerResult(
			analyzer_id='ai_crawlability',
			status='pass',
			score=0.95,
			source_evidence_ids=source_ids,
			page_url=primary_page_url(index_evidence, base_url),
			title='Indexed and crawlable',
			summary='Search Console reports the page is indexed; no crawl blockers detected in the current evidence.',
			severity='info',
			rationale='Google: indexed + crawlable is the prerequisite for AI Overview eligibility.',
			rationale_url=ai_guide_url(),
			metadata={'passed_verdicts': passed_verdicts},
		)

	return AiAnalyzerResult(
		analyzer_id='ai_crawlability',
		status='warn',
		score=0.6,
		source_evidence_ids=[e.evidence_id for e in relevant],
		title='Crawlability partially confirmed',
		summary='Some crawl evidence is available but the index verdict is unclear.',
		severity='low',
		rationale='Verify indexing in Search Console once GSC data is connected.',
		rationale_url=ai_guide_url(),
	)


def _index_verdict(item: SeoEvidenceRef) -> str:
	meta = item.metadata or {}
	verdict = meta.get('verdict')
	if isinstance(verdict, str) and verdict:
		return verdict.upper()
	inner = meta.get('indexStatusResult')
	if isinstance(inner, dict):
		v = inner.get('verdict')
		if isinstance(v, str):
			return v.upper()
	return ''


def _looks_like_blocker(item: SeoEvidenceRef) -> bool:
	text = ' '.join([item.title or '', item.summary or '']).lower()
	return any(phrase in text for phrase in _BLOCK_PHRASES) or _http_error(item)


def _http_error(item: SeoEvidenceRef) -> bool:
	if item.metric_unit != 'status_code' or item.metric_value is None:
		return False
	try:
		return int(item.metric_value) >= 400
	except (TypeError, ValueError):
		return False
