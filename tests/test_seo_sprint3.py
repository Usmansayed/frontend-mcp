"""Sprint 3 — AI reasoning + evidence validation tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.reasoning.ai_reasoner import try_ai_recommendations
from navigation.seo_intelligence.reasoning.context_v2 import build_reasoning_context_v2
from navigation.seo_intelligence.reasoning.enrichment import enrich_reasoning_context_v2
from navigation.seo_intelligence.reasoning.llm_client import ai_reasoning_enabled
from navigation.seo_intelligence.reasoning.prompt import build_ai_prompt_payload
from navigation.seo_intelligence.reasoning.validate import validate_draft_recommendations
from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline


class _MockLlm:
	def __init__(self, response: dict[str, Any] | None = None, *, available: bool = True) -> None:
		self._response = response or {}
		self._available = available

	def is_available(self) -> bool:
		return self._available

	def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
		return self._response


def _sample_context() -> tuple[dict[str, Any], list[SeoEvidenceRef]]:
	evidence = [
		SeoEvidenceRef(
			evidence_id='ev:gsc:index:abc123',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Index fail',
			summary='URL not indexed',
			page_url='https://example.com/pricing',
			severity='high',
			metadata={'verdict': 'FAIL', 'impressions': 1200},
		),
		SeoEvidenceRef(
			evidence_id='ev:browser:render:def456',
			provider_id='browser',
			kind=SeoEvidenceKind.RENDERING_ISSUE,
			title='Hydration error',
			summary='Client render mismatch',
			page_url='https://example.com/pricing',
			severity='high',
		),
	]
	correlations = [
		{
			'analysis_id': 'indexing_rendering_correlation',
			'title': 'Rendering may block indexing',
			'summary': 'Index failure with rendering errors on same URL',
			'root_cause': 'JS rendering issues',
			'business_impact': 'Lost organic traffic',
			'evidence_ids': ['ev:gsc:index:abc123', 'ev:browser:render:def456'],
			'page_url': 'https://example.com/pricing',
			'confidence': 0.82,
			'category': 'cross_analysis',
		},
	]
	ctx = build_reasoning_context_v2(
		audit_id='audit_s3',
		evidence=evidence,
		correlations=correlations,
		mode=SeoAuditMode.PROFESSIONAL,
		website_url='https://example.com',
		providers={'search-console': 'connected', 'browser': 'connected'},
	)
	ctx = enrich_reasoning_context_v2(ctx, evidence=evidence, base_url='https://example.com')
	return ctx, evidence


def test_prompt_payload_only_includes_unit_evidence() -> None:
	ctx, _ = _sample_context()
	payload = build_ai_prompt_payload(ctx, max_units=5)
	catalog = payload.get('evidence_catalog') or {}
	assert 'ev:gsc:index:abc123' in catalog
	assert 'ev:browser:render:def456' in catalog
	assert payload.get('constraints', {}).get('must_cite_evidence_ids') is True


def test_validate_rejects_unknown_evidence() -> None:
	ctx, _ = _sample_context()
	unit_id = ctx['reasoning_units'][0]['unit_id']
	drafts = [
		{
			'reasoning_unit_id': unit_id,
			'recommendation_id': 'indexing_rendering_correlation',
			'title': 'Fix rendering',
			'root_cause': 'Hydration blocks index',
			'fix_guidance': 'Fix SSR mismatch',
			'priority': 'high',
			'evidence_ids': ['ev:fake:missing:000'],
		},
	]
	accepted, errors = validate_draft_recommendations(drafts, reasoning_context_v2=ctx)
	assert not accepted
	assert any('unknown_evidence' in e for e in errors)


def test_validate_accepts_grounded_draft() -> None:
	ctx, _ = _sample_context()
	unit = ctx['reasoning_units'][0]
	drafts = [
		{
			'reasoning_unit_id': unit['unit_id'],
			'recommendation_id': 'indexing_rendering_correlation',
			'title': 'Fix rendering on pricing',
			'summary': 'Align server and client HTML',
			'root_cause': 'Hydration error prevents reliable indexing',
			'business_impact': 'Recover impressions on pricing page',
			'fix_guidance': 'Fix hydration; verify with perception_observe',
			'priority': 'high',
			'evidence_ids': list(unit['evidence_ids']),
		},
	]
	accepted, errors = validate_draft_recommendations(drafts, reasoning_context_v2=ctx)
	assert len(accepted) == 1
	assert not errors


def test_validate_rejects_invented_large_metrics() -> None:
	ctx, _ = _sample_context()
	unit = ctx['reasoning_units'][0]
	drafts = [
		{
			'reasoning_unit_id': unit['unit_id'],
			'title': 'Fix CTR',
			'root_cause': 'CTR dropped to 0.5% on 99999 impressions',
			'fix_guidance': 'Improve title tags',
			'priority': 'medium',
			'evidence_ids': list(unit['evidence_ids']),
		},
	]
	accepted, errors = validate_draft_recommendations(drafts, reasoning_context_v2=ctx)
	assert not accepted
	assert any('invented_metrics' in e for e in errors)


def test_ai_reasoner_uses_valid_llm_output() -> None:
	ctx, evidence = _sample_context()
	unit = ctx['reasoning_units'][0]
	mock = _MockLlm(
		{
			'recommendations': [
				{
					'reasoning_unit_id': unit['unit_id'],
					'recommendation_id': 'indexing_rendering_correlation',
					'title': 'Stabilize pricing page render',
					'summary': 'Fix hydration before requesting indexing',
					'root_cause': 'Client-only content hurts crawl/index',
					'business_impact': 'Restore organic visibility on pricing',
					'fix_guidance': 'Server-render critical content; fix hydration errors',
					'priority': 'high',
					'evidence_ids': list(unit['evidence_ids']),
				},
			],
		},
	)
	recs, meta = try_ai_recommendations(ctx, evidence, ai_reasoning=True, client=mock)
	assert recs is not None
	assert len(recs) == 1
	assert recs[0].metadata.get('source') == 'llm'
	assert meta['source'] == 'llm'


def test_ai_reasoner_partial_merges_with_deterministic() -> None:
	ctx, evidence = _sample_context()
	unit = ctx['reasoning_units'][0]
	mock = _MockLlm(
		{
			'recommendations': [
				{
					'reasoning_unit_id': unit['unit_id'],
					'recommendation_id': 'indexing_rendering_correlation',
					'title': 'Valid AI rec',
					'root_cause': 'Hydration blocks indexing',
					'fix_guidance': 'Fix SSR hydration',
					'priority': 'high',
					'evidence_ids': list(unit['evidence_ids']),
				},
				{
					'title': 'Invalid',
					'root_cause': 'bad',
					'fix_guidance': 'bad',
					'priority': 'high',
					'evidence_ids': [],
				},
			],
		},
	)
	recs, meta = try_ai_recommendations(ctx, evidence, ai_reasoning=True, client=mock)
	assert recs is not None
	assert len(recs) == 1
	assert meta['source'] == 'llm_partial'


def test_pipeline_deterministic_when_ai_disabled(monkeypatch) -> None:
	monkeypatch.setenv('SEO_SKIP_AI_REASONING', '1')
	evidence = [
		SeoEvidenceRef(
			evidence_id='ev:gsc:index:abc123',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Index fail',
			summary='FAIL',
			page_url='https://example.com/pricing',
			severity='high',
			metadata={'verdict': 'FAIL'},
		),
	]
	recs, _, ctx = run_recommendation_pipeline(
		evidence,
		audit_id='audit_pipe',
		mode=SeoAuditMode.PROFESSIONAL,
		website_url='https://example.com',
		ai_reasoning=True,
	)
	assert recs
	meta = ctx.get('ai_reasoning') or {}
	assert meta.get('source') == 'deterministic_fallback'
	assert ctx.get('sprint') == 'intelligence_v2'


def test_ai_reasoning_enabled_respects_env(monkeypatch) -> None:
	monkeypatch.setenv('SEO_AI_REASONING', '0')
	assert ai_reasoning_enabled(None) is False
	monkeypatch.delenv('SEO_AI_REASONING', raising=False)
	monkeypatch.setenv('SEO_SKIP_AI_REASONING', '1')
	assert ai_reasoning_enabled(None) is False
