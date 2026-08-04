"""AI extractability — can systems render and read the main content?

Sources:
- Google JavaScript SEO basics (https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- Core Web Vitals thresholds (https://web.dev/articles/vitals)
Rationale: AI features grounded in Google's index depend on the same
rendering signals traditional search does.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers._common import (
	ai_guide_url,
	evidence_by_kind,
	primary_page_url,
)
from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.models import SeoEvidenceRef

_INPUT_KINDS = {'rendering_issue', 'technical_issue', 'core_web_vital', 'performance'}

_LCP_GOOD_MS = 2500.0
_INP_GOOD_MS = 200.0
_CLS_GOOD = 0.1


def analyze(evidence: list[SeoEvidenceRef], base_url: str) -> AiAnalyzerResult:
	relevant = evidence_by_kind(evidence, _INPUT_KINDS)
	if not relevant:
		return AiAnalyzerResult(
			analyzer_id='ai_extractability',
			status='skipped',
			score=0.0,
			rationale='No rendering, technical, or Core Web Vital evidence available.',
			rationale_url=ai_guide_url(),
		)

	rendering_blockers = [
		e for e in relevant
		if e.kind.value == 'rendering_issue' and e.severity in {'high', 'critical'}
	]
	cwv_fails = [e for e in relevant if e.kind.value in {'core_web_vital', 'performance'} and _cwv_fails(e)]

	source_ids = [e.evidence_id for e in rendering_blockers + cwv_fails]
	if rendering_blockers:
		return AiAnalyzerResult(
			analyzer_id='ai_extractability',
			status='fail',
			score=0.2,
			source_evidence_ids=source_ids,
			page_url=primary_page_url(rendering_blockers, base_url),
			title='Rendering blockers prevent AI extraction',
			summary='Browser Intelligence reports hydration or client-side errors that block main content from being rendered for crawlers and AI systems.',
			severity='high',
			rationale='Google: if a page cannot be rendered, its content cannot be indexed or cited in AI features.',
			rationale_url='https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics',
			metadata={'blocker_count': len(rendering_blockers)},
		)

	if cwv_fails:
		return AiAnalyzerResult(
			analyzer_id='ai_extractability',
			status='warn',
			score=0.6,
			source_evidence_ids=source_ids,
			page_url=primary_page_url(cwv_fails, base_url),
			title='Core Web Vitals below "good" thresholds',
			summary='One or more Core Web Vitals are outside Google\'s "good" thresholds. Page experience contributes to overall ranking and to AI feature eligibility.',
			severity='medium',
			rationale='LCP <= 2.5s, INP <= 200ms, CLS <= 0.1 are the Google-recommended targets.',
			rationale_url='https://web.dev/articles/vitals',
			metadata={'failing_metrics': [_metric_summary(e) for e in cwv_fails[:5]]},
		)

	return AiAnalyzerResult(
		analyzer_id='ai_extractability',
		status='pass',
		score=0.9,
		source_evidence_ids=[e.evidence_id for e in relevant],
		page_url=primary_page_url(relevant, base_url),
		title='Page renders cleanly with good Web Vitals',
		summary='No blocking rendering issues; Core Web Vitals within Google thresholds where measured.',
		severity='info',
		rationale='Clean rendering + good Web Vitals is Google\'s foundational requirement for AI feature eligibility.',
		rationale_url=ai_guide_url(),
	)


def _cwv_fails(item: SeoEvidenceRef) -> bool:
	if item.metric_value is None:
		return False
	title = (item.title or '').lower()
	audit_id = str((item.metadata or {}).get('auditId') or '').lower()
	try:
		value = float(item.metric_value)
	except (TypeError, ValueError):
		return False
	if 'lcp' in title or 'largest-contentful-paint' in audit_id:
		return value > _LCP_GOOD_MS
	if 'cls' in title or 'cumulative-layout-shift' in audit_id:
		return value > _CLS_GOOD
	if 'inp' in title or 'interactive' in audit_id or 'tbt' in title or 'total-blocking-time' in audit_id:
		return value > _INP_GOOD_MS
	return item.severity in {'high', 'critical'}


def _metric_summary(item: SeoEvidenceRef) -> dict[str, object]:
	return {
		'evidence_id': item.evidence_id,
		'title': item.title,
		'metric_value': item.metric_value,
		'metric_unit': item.metric_unit,
	}
