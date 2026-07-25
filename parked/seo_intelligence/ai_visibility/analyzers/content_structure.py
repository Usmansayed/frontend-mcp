"""AI content structure — clear sections, headings, lists.

Google explicitly says to *ignore* "chunking" tactics for AI systems. This
analyzer instead rewards observable structural quality (heading hierarchy,
lists, sections). It is intentionally conservative: it only fires when a
provider surfaces structural signals.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'technical_issue', 'crawl_issue', 'rendering_issue'}
_PHRASES = ('wall of text', 'no section', 'no h2', 'no h3', 'missing subheading', 'no list', 'content structure')


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	hits = [e for e in relevant if matches_any_phrase(e, _PHRASES)]
	if not hits:
		return AiAnalyzerResult(
			analyzer_id='ai_content_structure',
			status='skipped',
			score=0.0,
			rationale='No content structure signals surfaced by current providers.',
			rationale_url=ai_guide_url(),
		)
	return AiAnalyzerResult(
		analyzer_id='ai_content_structure',
		status='warn',
		score=0.6,
		source_evidence_ids=[e.evidence_id for e in hits],
		title='Content structure could be improved',
		summary='Crawl or rendering signals suggest wall-of-text sections or missing subheadings. Use H2/H3 and lists for clear structure — not artificial chunking.',
		severity='low',
		rationale='Google: reward clear structure; explicitly do not use artificial chunking or AI-only markup.',
		rationale_url=ai_guide_url(),
	)
