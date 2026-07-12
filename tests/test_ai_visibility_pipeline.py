"""AI Visibility layer — pipeline integration and toggle behavior."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline


def _sample_evidence() -> list[SeoEvidenceRef]:
	return [
		SeoEvidenceRef(
			evidence_id='ev:gsc:index:1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Index status: https://example.com/',
			summary='PASS',
			page_url='https://example.com/',
			metadata={'verdict': 'PASS'},
		),
		SeoEvidenceRef(
			evidence_id='ev:libre:schema',
			provider_id='librecrawl',
			kind=SeoEvidenceKind.CRAWL_ISSUE,
			title='No Structured Data',
			summary='Page has no JSON-LD or Schema.org markup',
			page_url='https://example.com/',
			severity='medium',
			metadata={'category': 'Structured Data'},
		),
		SeoEvidenceRef(
			evidence_id='ev:lh:meta',
			provider_id='lighthouse',
			kind=SeoEvidenceKind.TECHNICAL_ISSUE,
			title='Document does not have a meta description',
			summary='...',
			page_url='https://example.com/',
			severity='high',
		),
	]


def test_pipeline_produces_ai_readiness_recs() -> None:
	recs, correlations, ctx = run_recommendation_pipeline(
		_sample_evidence(),
		audit_id='audit_ai_test',
		mode=SeoAuditMode.DEVELOPMENT,
		website_url='https://example.com/',
		ai_reasoning=False,
	)
	ai_recs = [r for r in recs if r.category == 'ai_visibility']
	assert ai_recs, 'expected at least one ai_visibility recommendation'
	for rec in ai_recs:
		assert rec.evidence_ids, 'AI rec must cite evidence'
		assert rec.fix_guidance, 'AI rec must include fix guidance'

	ai_corrs = [c for c in correlations if c.get('category') == 'ai_visibility']
	assert ai_corrs

	block = ctx.get('ai_readiness') or {}
	assert block, 'ai_readiness block should be attached'
	assert block.get('dimensions')


def test_pipeline_skips_ai_visibility_when_disabled() -> None:
	recs, correlations, ctx = run_recommendation_pipeline(
		_sample_evidence(),
		audit_id='audit_ai_off',
		mode=SeoAuditMode.DEVELOPMENT,
		website_url='https://example.com/',
		ai_reasoning=False,
		include_ai_visibility=False,
	)
	assert not any(r.category == 'ai_visibility' for r in recs)
	assert not any(c.get('category') == 'ai_visibility' for c in correlations)
	assert 'ai_readiness' not in ctx
