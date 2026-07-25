"""AI entity coverage — is Schema.org JSON-LD present for the primary entity?

Source: Google — Introduction to structured data
(https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data).
Google explicitly says AI features do not require special schema, but valid
Schema.org markup helps disambiguate entities. We only recommend *standard*
vocabulary — never AI-specific types.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	evidence_by_kind,
	matches_any_phrase,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'schema', 'crawl_issue', 'technical_issue'}
_MISSING_PHRASES = ('no structured data', 'no json-ld', 'missing schema', 'no schema', 'structured data')
_STRUCTURED_DATA_URL = 'https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data'


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_entity_coverage',
			status='skipped',
			score=0.0,
			rationale='No structured-data related evidence collected.',
			rationale_url=_STRUCTURED_DATA_URL,
		)

	schema_evidence = [e for e in relevant if e.kind.value == 'schema']
	missing_hits = [e for e in relevant if matches_any_phrase(e, _MISSING_PHRASES)]

	if not schema_evidence and missing_hits:
		return AiAnalyzerResult(
			analyzer_id='ai_entity_coverage',
			status='fail',
			score=0.2,
			source_evidence_ids=[e.evidence_id for e in missing_hits],
			page_url=primary_page_url(missing_hits, base_url),
			title='No JSON-LD structured data detected',
			summary='Crawl reports no Schema.org JSON-LD on the page. Standard vocabulary (Organization, WebSite, Product, SoftwareApplication, Article) helps AI systems and Search understand the primary entity.',
			severity='high',
			rationale='Google structured data guide: valid schema helps AI systems disambiguate entities; no "AI schema type" exists — use standard Schema.org vocabulary.',
			rationale_url=_STRUCTURED_DATA_URL,
			metadata={'recommended_types': ['Organization', 'WebSite', 'Product', 'SoftwareApplication', 'Article']},
		)

	if schema_evidence:
		return AiAnalyzerResult(
			analyzer_id='ai_entity_coverage',
			status='pass',
			score=0.85,
			source_evidence_ids=[e.evidence_id for e in schema_evidence],
			page_url=primary_page_url(schema_evidence, base_url),
			title='Structured data present',
			summary=f'{len(schema_evidence)} Schema.org markup signal(s) detected on crawled pages.',
			severity='info',
			rationale='Schema.org markup is optional for AI features but helps entity clarity.',
			rationale_url=_STRUCTURED_DATA_URL,
		)

	return AiAnalyzerResult(
		analyzer_id='ai_entity_coverage',
		status='skipped',
		score=0.0,
		rationale='Structured-data-related evidence exists but no direct schema signal was found.',
		rationale_url=_STRUCTURED_DATA_URL,
	)
