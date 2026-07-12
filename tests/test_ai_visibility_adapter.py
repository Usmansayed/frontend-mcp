"""AI Visibility adapter — derives evidence with stable IDs, upserts to graph."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import pytest

from navigation.seo_intelligence.ai_visibility.adapter import AiVisibilityAdapter
from navigation.seo_intelligence.ai_visibility.analysis import detect_ai_readiness
from navigation.seo_intelligence.ai_visibility.enrich import attach_ai_readiness_block
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef


@pytest.fixture
def strikeloop_like_evidence() -> list[SeoEvidenceRef]:
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
			evidence_id='ev:lh:meta',
			provider_id='lighthouse',
			kind=SeoEvidenceKind.TECHNICAL_ISSUE,
			title='Document does not have a meta description',
			summary='...',
			page_url='https://example.com/',
			severity='high',
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
	]


def test_adapter_produces_ai_visibility_evidence(strikeloop_like_evidence) -> None:
	derived, degraded = AiVisibilityAdapter().derive(
		strikeloop_like_evidence,
		base_url='https://example.com/',
	)
	assert derived
	for item in derived:
		assert item.provider_id == 'ai-visibility'
		assert item.kind == SeoEvidenceKind.AI_VISIBILITY
		assert item.metric_unit == 'score'
		assert item.metadata.get('analyzer_id')
		assert 'source_evidence_ids' in item.metadata
	assert any(n.startswith('ai_readiness_insufficient_evidence:') for n in degraded)


def test_adapter_ids_stable_across_runs(strikeloop_like_evidence) -> None:
	first, _ = AiVisibilityAdapter().derive(strikeloop_like_evidence, base_url='https://example.com/')
	second, _ = AiVisibilityAdapter().derive(strikeloop_like_evidence, base_url='https://example.com/')
	assert [e.evidence_id for e in first] == [e.evidence_id for e in second]


def test_correlations_and_readiness_block(strikeloop_like_evidence) -> None:
	derived, _ = AiVisibilityAdapter().derive(strikeloop_like_evidence, base_url='https://example.com/')
	full = strikeloop_like_evidence + derived

	correlations = detect_ai_readiness(full, base_url='https://example.com/')
	assert correlations
	for corr in correlations:
		assert corr['category'] == 'ai_visibility'
		assert corr['analysis_id'].startswith('ai_readiness_')
		assert corr['evidence_ids']

	ctx = attach_ai_readiness_block({}, evidence=full)
	block = ctx['ai_readiness']
	assert 0.0 <= block['overall_score'] <= 1.0
	assert block['dimensions']
	assert 'sources_documented_in' in block


def test_graph_upsert_puts_ai_evidence_in_ai_signals(tmp_path, strikeloop_like_evidence) -> None:
	store = SeoKnowledgeGraphStore(path=tmp_path / 'graph.json')
	derived, _ = AiVisibilityAdapter().derive(strikeloop_like_evidence, base_url='https://example.com/')
	for item in derived:
		store.upsert_evidence(item, base_url='https://example.com/')
	data = store.load()
	assert data['ai_signals']
	for evidence_id in data['ai_signals']:
		assert evidence_id.startswith('ev:ai-visibility:ai_visibility:')
