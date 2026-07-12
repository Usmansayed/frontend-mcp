"""AI Visibility analyzers — evidence-driven behavior + skip-when-missing."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.seo_intelligence.ai_visibility.analyzers import registry
from navigation.seo_intelligence.ai_visibility.analyzers.citation_readiness import analyze as citation_readiness
from navigation.seo_intelligence.ai_visibility.analyzers.crawlability import analyze as crawlability
from navigation.seo_intelligence.ai_visibility.analyzers.entity_coverage import analyze as entity_coverage
from navigation.seo_intelligence.ai_visibility.analyzers.extractability import analyze as extractability
from navigation.seo_intelligence.ai_visibility.analyzers.semantic_html import analyze as semantic_html
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


def _ev(
	evidence_id: str,
	provider_id: str,
	kind: SeoEvidenceKind,
	title: str,
	*,
	summary: str = '',
	page_url: str = 'https://example.com/',
	severity: str = 'info',
	metric_value: float | None = None,
	metric_unit: str = '',
	metadata: dict | None = None,
) -> SeoEvidenceRef:
	return SeoEvidenceRef(
		evidence_id=evidence_id,
		provider_id=provider_id,
		kind=kind,
		title=title,
		summary=summary or title,
		page_url=page_url,
		severity=severity,
		metric_value=metric_value,
		metric_unit=metric_unit,
		metadata=metadata or {},
	)


def test_registered_analyzer_ids_stable() -> None:
	ids = registry.registered_analyzer_ids()
	assert ids[0] == 'ai_crawlability'
	assert 'ai_llms_txt_optional' in ids
	assert len(ids) == 12


def test_analyzers_skip_when_no_evidence() -> None:
	for analyzer_id, fn in zip(
		('ai_crawlability', 'ai_extractability', 'ai_citation_readiness', 'ai_entity_coverage', 'ai_semantic_html'),
		(crawlability, extractability, citation_readiness, entity_coverage, semantic_html),
	):
		result = fn([], 'https://example.com/')
		assert result.status == 'skipped', analyzer_id
		assert result.score == 0.0


def test_crawlability_fails_when_index_verdict_fail() -> None:
	ev = [
		_ev(
			'ev:gsc:index:1',
			'search-console',
			SeoEvidenceKind.INDEX_STATUS,
			'Index status',
			summary='not indexed',
			metadata={'verdict': 'FAIL'},
		),
	]
	result = crawlability(ev, 'https://example.com/')
	assert result.status == 'fail'
	assert result.severity == 'high'
	assert 'ev:gsc:index:1' in result.source_evidence_ids


def test_crawlability_passes_on_indexed() -> None:
	ev = [
		_ev(
			'ev:gsc:index:2',
			'search-console',
			SeoEvidenceKind.INDEX_STATUS,
			'Index status',
			metadata={'verdict': 'PASS'},
		),
	]
	result = crawlability(ev, 'https://example.com/')
	assert result.status == 'pass'


def test_citation_readiness_flags_missing_meta_description() -> None:
	ev = [
		_ev(
			'ev:lh:meta',
			'lighthouse',
			SeoEvidenceKind.TECHNICAL_ISSUE,
			'Document does not have a meta description',
			severity='high',
		),
	]
	result = citation_readiness(ev, 'https://example.com/')
	assert result.status == 'fail'
	assert 'meta_description' in result.metadata['missing_fields']


def test_entity_coverage_fails_when_no_structured_data() -> None:
	ev = [
		_ev(
			'ev:libre:schema',
			'librecrawl',
			SeoEvidenceKind.CRAWL_ISSUE,
			'No Structured Data',
			summary='Page has no JSON-LD or Schema.org markup',
			severity='medium',
			metadata={'category': 'Structured Data'},
		),
	]
	result = entity_coverage(ev, 'https://example.com/')
	assert result.status == 'fail'
	assert result.severity == 'high'


def test_extractability_warns_on_bad_lcp() -> None:
	ev = [
		_ev(
			'ev:lh:lcp',
			'lighthouse',
			SeoEvidenceKind.CORE_WEB_VITAL,
			'LCP: 3.2s',
			metric_value=3200.0,
			metric_unit='ms',
			metadata={'auditId': 'largest-contentful-paint'},
			severity='medium',
		),
	]
	result = extractability(ev, 'https://example.com/')
	assert result.status == 'warn'


def test_semantic_html_warns_on_heading_issues() -> None:
	ev = [
		_ev(
			'ev:lh:heading',
			'lighthouse',
			SeoEvidenceKind.TECHNICAL_ISSUE,
			'Heading order is invalid (heading-order)',
			severity='medium',
		),
	]
	result = semantic_html(ev, 'https://example.com/')
	assert result.status == 'warn'
