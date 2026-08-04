"""AI schema quality — is present JSON-LD valid?

Source: Schema.org vocabulary + Google rich-results guide
(https://developers.google.com/search/docs/appearance/structured-data/search-gallery).
Skipped unless a schema evidence item exists. Never asks for AI-only schema.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	evidence_by_kind,
	matches_any_phrase,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'schema', 'crawl_issue', 'technical_issue'}
_ERROR_PHRASES = ('invalid schema', 'malformed', 'json-ld error', 'schema parse', 'invalid structured', 'schema error')
_RICH_RESULTS_URL = 'https://developers.google.com/search/docs/appearance/structured-data/search-gallery'


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	schema_related = evidence_by_kind(evidence, _INPUT_KINDS)
	schema_evidence = [e for e in schema_related if e.kind.value == 'schema']
	errors = [e for e in schema_related if matches_any_phrase(e, _ERROR_PHRASES)]

	if not schema_evidence and not errors:
		return AiAnalyzerResult(
			analyzer_id='ai_schema_quality',
			status='skipped',
			score=0.0,
			rationale='No JSON-LD schema evidence available to validate.',
			rationale_url=_RICH_RESULTS_URL,
		)

	if errors:
		return AiAnalyzerResult(
			analyzer_id='ai_schema_quality',
			status='fail',
			score=0.25,
			source_evidence_ids=[e.evidence_id for e in errors],
			title='Structured data errors',
			summary='Crawl reports invalid or malformed Schema.org markup. Google\'s rich-results tester will reject broken JSON-LD.',
			severity='high',
			rationale='Schema.org requires valid vocabulary and JSON syntax. Fix errors before shipping.',
			rationale_url=_RICH_RESULTS_URL,
		)

	return AiAnalyzerResult(
		analyzer_id='ai_schema_quality',
		status='pass',
		score=0.85,
		source_evidence_ids=[e.evidence_id for e in schema_evidence],
		title='No structured data errors detected',
		summary='Schema evidence is present and no parse errors were reported.',
		severity='info',
		rationale='Valid JSON-LD is a necessary condition for rich results and helps entity extraction.',
		rationale_url=_RICH_RESULTS_URL,
	)
