"""AI trust signals — objective identity signals only.

Source: Google's helpful-content and E-E-A-T guidance
(https://developers.google.com/search/docs/fundamentals/creating-helpful-content).
We only surface observable, mechanical signals: Organization schema, author
byline evidence, ``sameAs`` links. No subjective judgment.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	evidence_by_kind,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'schema', 'crawl_issue', 'technical_issue', 'index_status'}
_HAS_ORG_PHRASES = ('organization', 'sameas', 'author', 'byline')
_MISSING_ORG_PHRASES = ('no structured data', 'missing organization', 'missing author', 'no schema')
_EEAT_URL = 'https://developers.google.com/search/docs/fundamentals/creating-helpful-content'


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_trust_signals',
			status='skipped',
			score=0.0,
			rationale='No schema, crawl, or index_status evidence to evaluate trust signals.',
			rationale_url=_EEAT_URL,
		)

	has_hits = [e for e in relevant if matches_any_phrase(e, _HAS_ORG_PHRASES) and e.kind.value == 'schema']
	missing_hits = [e for e in relevant if matches_any_phrase(e, _MISSING_ORG_PHRASES)]

	if has_hits:
		return AiAnalyzerResult(
			analyzer_id='ai_trust_signals',
			status='pass',
			score=0.85,
			source_evidence_ids=[e.evidence_id for e in has_hits],
			title='Identity signals present',
			summary='Organization / author / sameAs signals detected in crawled schema evidence.',
			severity='info',
			rationale='Objective E-E-A-T signals: publisher identity + sameAs links help AI systems attribute content.',
			rationale_url=_EEAT_URL,
		)

	if missing_hits:
		return AiAnalyzerResult(
			analyzer_id='ai_trust_signals',
			status='warn',
			score=0.5,
			source_evidence_ids=[e.evidence_id for e in missing_hits],
			title='No publisher identity signals detected',
			summary='No Organization schema, sameAs links, or author byline signals present. Adding Organization JSON-LD with sameAs (LinkedIn, GitHub, X) helps AI systems attribute content correctly.',
			severity='medium',
			rationale='Google E-E-A-T guidance: signal publisher identity clearly; do not fabricate credentials.',
			rationale_url=_EEAT_URL,
		)

	return AiAnalyzerResult(
		analyzer_id='ai_trust_signals',
		status='skipped',
		score=0.0,
		rationale='Trust-related evidence exists but did not match observable identity signals.',
		rationale_url=_EEAT_URL,
	)
