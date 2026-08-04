"""Visible Q&A / answer blocks — never asks for FAQPage schema (deprecated).

Source: Google's rich-results changelog notes FAQ rich results were retired
(May 2026). Visible Q&A structure in HTML remains valuable for AI extraction;
FAQ JSON-LD is not.

This analyzer is intentionally conservative: it only reports when a provider
explicitly surfaces Q&A-related signals (LibreCrawl "faq_missing" hints,
browser DOM notes). Otherwise it skips.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'crawl_issue', 'technical_issue', 'rendering_issue'}
_PHRASES = ('faq', 'q&a', 'question and answer', 'answer block')


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	hits = [e for e in relevant if matches_any_phrase(e, _PHRASES)]
	if not hits:
		return AiAnalyzerResult(
			analyzer_id='ai_faq_answer_blocks',
			status='skipped',
			score=0.0,
			rationale='No Q&A signals surfaced by current providers.',
			rationale_url=ai_guide_url(),
		)
	return AiAnalyzerResult(
		analyzer_id='ai_faq_answer_blocks',
		status='warn',
		score=0.6,
		source_evidence_ids=[e.evidence_id for e in hits],
		title='Visible Q&A structure could be improved',
		summary='Provider evidence flags Q&A-related issues. Prefer visible, heading-based Q&A over FAQPage JSON-LD (FAQ rich results retired May 2026).',
		severity='low',
		rationale='Google: prefer visible, heading-based answers over markup hacks.',
		rationale_url=ai_guide_url(),
	)
