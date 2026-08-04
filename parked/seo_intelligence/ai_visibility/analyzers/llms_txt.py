"""Informational-only observation of /llms.txt.

Google explicitly says llms.txt is not needed and should be ignored as a
tactic. This analyzer never recommends creating one. It just reports presence
if the crawler happened to encounter the file so agents can surface the fact.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_PHRASES = ('llms.txt', '/llms.txt')


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	hits = [e for e in evidence if matches_any_phrase(e, _PHRASES)]
	if not hits:
		return AiAnalyzerResult(
			analyzer_id='ai_llms_txt_optional',
			status='skipped',
			score=0.0,
			rationale='No evidence about /llms.txt; nothing to report.',
			rationale_url=ai_guide_url(),
		)
	return AiAnalyzerResult(
		analyzer_id='ai_llms_txt_optional',
		status='pass',
		score=1.0,
		source_evidence_ids=[e.evidence_id for e in hits],
		title='llms.txt observed',
		summary='An /llms.txt file was observed. This is informational — Google\'s guidance says llms.txt is not required for AI features and does not affect ranking.',
		severity='info',
		rationale='Google explicitly rejects llms.txt as an AI-optimization tactic. Reporting presence only.',
		rationale_url=ai_guide_url(),
		metadata={'observed_count': len(hits)},
	)
