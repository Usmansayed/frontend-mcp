"""Tests for evidence-first SEO Sprint 1 (ADR-027)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence.evidence.identity import normalize_page_url, stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.reasoning.confidence import compose_confidence, confidence_label
from navigation.seo_intelligence.reasoning.context_v2 import REASONING_CONTEXT_V2_VERSION, build_reasoning_context_v2
from navigation.seo_intelligence.verification.loop import evaluate_verification
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult, SeoRecommendation


def test_stable_evidence_id_is_deterministic() -> None:
	a = stable_evidence_id(
		'search-console',
		'index_status',
		page_url='https://example.com/pricing',
		source_ref='urlInspection.index',
	)
	b = stable_evidence_id(
		'search-console',
		'index_status',
		page_url='https://example.com/pricing',
		source_ref='urlInspection.index',
	)
	assert a == b
	assert a.startswith('ev:search-console:')


def test_normalize_page_url() -> None:
	assert normalize_page_url('https://Example.com/pricing/') == 'https://example.com/pricing'
	assert normalize_page_url('/pricing', base_url='https://example.com') == 'https://example.com/pricing'


def test_compose_confidence_multi_provider() -> None:
	evidence = [
		SeoEvidenceRef(
			evidence_id='e1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='FAIL',
			summary='not indexed',
			severity='high',
			metadata={'impressions': 500},
		),
		SeoEvidenceRef(
			evidence_id='e2',
			provider_id='browser',
			kind=SeoEvidenceKind.RENDERING_ISSUE,
			title='Hydration',
			summary='error',
			severity='high',
		),
	]
	conf = compose_confidence(evidence, providers_present=['search-console', 'browser'])
	assert conf['score'] > 0.3
	assert conf['composition']['provider_agreement'] >= 0.5
	assert len(conf['providers_present']) == 2


def test_reasoning_context_v2_schema() -> None:
	evidence = [
		SeoEvidenceRef(
			evidence_id=stable_evidence_id('browser', 'rendering_issue', page_url='https://example.com', title='err'),
			provider_id='browser',
			kind=SeoEvidenceKind.RENDERING_ISSUE,
			title='err',
			summary='hydration',
			page_url='https://example.com',
			severity='high',
		),
	]
	ctx = build_reasoning_context_v2(
		audit_id='audit_test1',
		evidence=evidence,
		correlations=[],
		mode=__import__('navigation.seo_intelligence.models', fromlist=['SeoAuditMode']).SeoAuditMode.DEVELOPMENT,
		website_url='https://example.com',
		providers={'browser': 'connected'},
	)
	assert ctx['schema_version'] == REASONING_CONTEXT_V2_VERSION
	assert ctx['meta']['audit_id'] == 'audit_test1'
	assert ctx['pages']
	assert 'reasoning_units' in ctx
	assert ctx['constraints']['must_cite_evidence_ids'] is True


def test_metric_verification_lcp_improved() -> None:
	eid = stable_evidence_id('lighthouse', 'core_web_vital', page_url='https://example.com', metric_key='lcp')
	baseline = SeoAuditResult(
		request=SeoAuditRequest(website_url='https://example.com'),
		evidence=[
			SeoEvidenceRef(
				evidence_id=eid,
				provider_id='lighthouse',
				kind=SeoEvidenceKind.CORE_WEB_VITAL,
				title='LCP',
				summary='slow',
				metric_value=4500.0,
				metric_unit='ms',
				severity='high',
				metadata={'auditId': 'largest-contentful-paint'},
			),
		],
		recommendations=[
			SeoRecommendation(
				recommendation_id='rec_lcp',
				title='Fix LCP',
				summary='slow',
				priority='high',
				category='core_web_vital',
				evidence_ids=[eid],
			),
		],
	)
	current = SeoAuditResult(
		request=SeoAuditRequest(website_url='https://example.com'),
		evidence=[
			SeoEvidenceRef(
				evidence_id=eid,
				provider_id='lighthouse',
				kind=SeoEvidenceKind.CORE_WEB_VITAL,
				title='LCP',
				summary='better',
				metric_value=2200.0,
				metric_unit='ms',
				severity='medium',
				metadata={'auditId': 'largest-contentful-paint'},
			),
		],
	)
	result = evaluate_verification(baseline=baseline, current=current, recommendation_ids=['rec_lcp'])
	assert result['passed_count'] == 1


def test_confidence_label_thresholds() -> None:
	assert confidence_label(0.9) == 'high'
	assert confidence_label(0.7) == 'medium'
	assert confidence_label(0.3) == 'low'
