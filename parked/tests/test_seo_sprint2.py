"""Sprint 2 — intelligence layer tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceKind, SeoEvidenceRef, SeoRecommendation
from navigation.seo_intelligence.reasoning.enrichment import enrich_reasoning_context_v2
from navigation.seo_intelligence.reasoning.impact import score_impact
from navigation.seo_intelligence.reasoning.context_v2 import build_reasoning_context_v2
from navigation.seo_intelligence.recommendations.dedupe import dedupe_recommendations
from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline


def test_impact_scores_high_traffic_index_fail() -> None:
	evidence = [
		SeoEvidenceRef(
			evidence_id='e1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Index fail',
			summary='FAIL',
			severity='high',
			metadata={'verdict': 'FAIL', 'impressions': 3000},
		),
	]
	impact = score_impact(evidence, page_url='https://example.com/pricing')
	assert float(impact['score']) >= 0.5
	assert impact['label'] in {'medium', 'high'}


def test_dedupe_recommendations_same_page_metadata() -> None:
	recs = [
		SeoRecommendation(
			recommendation_id='dev_practice_metadata',
			title='Meta A',
			summary='a',
			priority='high',
			category='development_practice',
			evidence_ids=['e1'],
			metadata={'page_url': 'https://example.com/pricing'},
		),
		SeoRecommendation(
			recommendation_id='opportunity_weak_metadata',
			title='Meta B',
			summary='b',
			priority='medium',
			category='opportunity',
			evidence_ids=['e2'],
			metadata={'page_url': 'https://example.com/pricing'},
		),
	]
	merged = dedupe_recommendations(recs)
	assert len(merged) == 1
	assert set(merged[0].evidence_ids) == {'e1', 'e2'}


def test_enrichment_adds_codebase_hints() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		page = root / 'app' / 'pricing' / 'page.tsx'
		page.parent.mkdir(parents=True)
		page.write_text(
			'export const metadata = { title: "Pricing" };\nexport default function Page() { return <h1>Pricing</h1> }',
			encoding='utf-8',
		)
		evidence = [
			SeoEvidenceRef(
				evidence_id='t1',
				provider_id='librecrawl',
				kind=SeoEvidenceKind.TECHNICAL_ISSUE,
				title='Missing meta description',
				summary='thin',
				page_url='https://example.com/pricing',
				severity='medium',
			),
		]
		ctx = build_reasoning_context_v2(
			audit_id='audit_x',
			evidence=evidence,
			correlations=[],
			mode=SeoAuditMode.DEVELOPMENT,
			website_url='https://example.com',
			providers={},
		)
		enriched = enrich_reasoning_context_v2(
			ctx,
			evidence=evidence,
			repo_root=str(root),
			base_url='https://example.com',
		)
		assert enriched.get('sprint') == 'intelligence_v2'
		page_entities = enriched.get('pages') or []
		assert page_entities
		assert page_entities[0].get('codebase_hints')


def test_pipeline_ranks_reasoning_units_by_impact() -> None:
	evidence = [
		SeoEvidenceRef(
			evidence_id='q1',
			provider_id='search-console',
			kind=SeoEvidenceKind.SEARCH_QUERY,
			title='big query',
			summary='',
			metadata={'impressions': 5000, 'ctr': 0.005, 'position': 5},
		),
	]
	_, _, ctx = run_recommendation_pipeline(
		evidence,
		audit_id='audit_rank',
		mode=SeoAuditMode.PROFESSIONAL,
		website_url='https://example.com',
	)
	units = ctx.get('reasoning_units') or []
	if len(units) >= 2:
		assert float(units[0].get('impact', {}).get('score', 0)) >= float(units[1].get('impact', {}).get('score', 0))
