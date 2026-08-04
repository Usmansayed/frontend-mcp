"""AI crawler access — reports observed robots.txt rules for AI crawlers.

Purely informational: allowing or blocking GPTBot / ClaudeBot / PerplexityBot
is a site owner choice. Google's guide never asks sites to allow any specific
AI crawler. This analyzer only reports what upstream crawl evidence surfaces.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'crawl_issue', 'technical_issue'}
_AI_BOTS = (
	'gptbot',
	'chatgpt-user',
	'claudebot',
	'anthropic-ai',
	'perplexitybot',
	'google-extended',
	'applebot-extended',
	'ccbot',
)


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	matches = [e for e in relevant if matches_any_phrase(e, _AI_BOTS)]
	if not matches:
		return AiAnalyzerResult(
			analyzer_id='ai_crawler_access',
			status='skipped',
			score=0.0,
			rationale='No crawl evidence mentions AI crawler user-agents; nothing to report.',
			rationale_url=ai_guide_url(),
		)

	observed = sorted({
		bot
		for item in matches
		for bot in _AI_BOTS
		if bot in (item.title + ' ' + item.summary).lower()
	})
	return AiAnalyzerResult(
		analyzer_id='ai_crawler_access',
		status='warn' if observed else 'pass',
		score=0.7,
		source_evidence_ids=[e.evidence_id for e in matches],
		title='AI crawler access rules observed',
		summary=f'robots.txt or crawl evidence mentions AI user-agents: {", ".join(observed)}.',
		severity='info',
		rationale='Blocking or allowing AI crawlers is a policy choice. This is reported so agents can surface it, not scored against the site.',
		rationale_url='https://developers.google.com/search/docs/crawling-indexing/robots/intro',
		metadata={'observed_bots': observed},
	)
