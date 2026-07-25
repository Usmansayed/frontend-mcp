"""Golden regression suite — fixture evidence → expected pipeline outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence.knowledge.graph.issue_class import provider_agreement_v2
from navigation.seo_intelligence.knowledge.graph.api import SeoGraphAPI
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.reasoning.ai_reasoner import try_ai_recommendations
from navigation.seo_intelligence.reasoning.confidence import compose_confidence
from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline

GOLDEN_DIR = Path(__file__).resolve().parent / 'fixtures' / 'seo_golden'


def _load_golden_cases() -> list[pytest.ParameterSet]:
	cases: list[pytest.ParameterSet] = []
	if not GOLDEN_DIR.is_dir():
		return cases
	for path in sorted(GOLDEN_DIR.glob('*.json')):
		payload = json.loads(path.read_text(encoding='utf-8'))
		cases.append(pytest.param(payload, id=payload.get('name') or path.stem))
	return cases


def _evidence_from_fixture(rows: list[dict]) -> list[SeoEvidenceRef]:
	out: list[SeoEvidenceRef] = []
	for row in rows:
		out.append(
			SeoEvidenceRef(
				evidence_id=str(row['evidence_id']),
				provider_id=str(row['provider_id']),
				kind=SeoEvidenceKind(str(row['kind'])),
				title=str(row.get('title') or ''),
				summary=str(row.get('summary') or ''),
				url=str(row.get('url') or ''),
				page_url=str(row.get('page_url') or ''),
				metric_value=row.get('metric_value'),
				metric_unit=str(row.get('metric_unit') or ''),
				severity=str(row.get('severity') or 'info'),
				source_ref=str(row.get('source_ref') or ''),
				metadata=dict(row.get('metadata') or {}),
			)
		)
	return out


@pytest.mark.parametrize('case', _load_golden_cases())
def test_golden_pipeline(case: dict) -> None:
	evidence = _evidence_from_fixture(case['evidence'])
	mode = SeoAuditMode.PROFESSIONAL if case.get('mode') == 'professional' else SeoAuditMode.DEVELOPMENT
	expect = case.get('expect') or {}

	recs, correlations, ctx = run_recommendation_pipeline(
		evidence,
		audit_id=f"golden_{case.get('name', 'case')}",
		mode=mode,
		website_url=str(case.get('website_url') or 'https://example.com'),
		ai_reasoning=False,
	)

	corr_ids = {str(c.get('analysis_id') or '') for c in correlations}
	for required in expect.get('correlation_ids_contains') or []:
		assert any(required in cid for cid in corr_ids), f'missing correlation {required} in {corr_ids}'

	units = ctx.get('reasoning_units') or []
	assert len(units) >= int(expect.get('min_reasoning_units') or 0)
	assert len(recs) >= int(expect.get('min_recommendations') or 0)

	if expect.get('page_urls_contains'):
		unit_urls = {str(u.get('page_url') or '') for u in units}
		for url in expect['page_urls_contains']:
			assert url in unit_urls

	min_agreement = expect.get('provider_agreement_v2_min')
	if min_agreement is not None and evidence:
		block = provider_agreement_v2(
			evidence,
			page_url=str(expect.get('page_urls_contains', [''])[0]),
		)
		assert float(block['score']) >= float(min_agreement)


def test_graph_query_page_issues() -> None:
	import tempfile

	evidence = _evidence_from_fixture(
		json.loads((GOLDEN_DIR / 'pricing_index_render.json').read_text(encoding='utf-8'))['evidence']
	)
	with tempfile.TemporaryDirectory() as tmp:
		store = SeoKnowledgeGraphStore(path=Path(tmp) / 'graph.json')
		store.set_website('https://example.com')
		for item in evidence:
			store.upsert_evidence(item, base_url='https://example.com')
		store.save()

		api = SeoGraphAPI(store)
		out = api.query('page.issues', {'page_url': 'https://example.com/pricing'})
		assert out['ok'] is True
		result = out['result']
		assert result['issue_count'] >= 2


def test_partial_ai_validation_accepts_valid_only() -> None:
	from navigation.seo_intelligence.reasoning.context_v2 import build_reasoning_context_v2
	from navigation.seo_intelligence.reasoning.enrichment import enrich_reasoning_context_v2

	evidence = _evidence_from_fixture(
		json.loads((GOLDEN_DIR / 'pricing_index_render.json').read_text(encoding='utf-8'))['evidence']
	)
	correlations = [
		{
			'analysis_id': 'indexing_rendering_correlation',
			'title': 'Rendering may block indexing',
			'summary': 'Index failure with rendering errors',
			'root_cause': 'JS rendering',
			'business_impact': 'Traffic loss',
			'evidence_ids': [e.evidence_id for e in evidence[:2]],
			'page_url': 'https://example.com/pricing',
			'category': 'cross_analysis',
		},
	]
	ctx = build_reasoning_context_v2(
		audit_id='audit_partial',
		evidence=evidence,
		correlations=correlations,
		mode=SeoAuditMode.PROFESSIONAL,
		website_url='https://example.com',
		providers={},
	)
	ctx = enrich_reasoning_context_v2(ctx, evidence=evidence, base_url='https://example.com')
	unit = ctx['reasoning_units'][0]

	class _MockLlm:
		def is_available(self) -> bool:
			return True

		def complete_json(self, *, system: str, user: str) -> dict:
			return {
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
						'title': 'Invalid — no evidence',
						'root_cause': 'bad',
						'fix_guidance': 'bad',
						'priority': 'high',
						'evidence_ids': [],
					},
				],
			}

	recs, meta = try_ai_recommendations(ctx, evidence, ai_reasoning=True, client=_MockLlm())
	assert recs is not None
	assert len(recs) == 1
	assert meta['source'] == 'llm_partial'
	assert meta['rejected_count'] == 1


def test_provider_agreement_v2_multi_provider_same_issue() -> None:
	evidence = _evidence_from_fixture(
		json.loads((GOLDEN_DIR / 'pricing_index_render.json').read_text(encoding='utf-8'))['evidence']
	)
	block = provider_agreement_v2(evidence, page_url='https://example.com/pricing')
	assert float(block['score']) > 0.3
	conf = compose_confidence(evidence)
	assert 'provider_agreement_v2' in conf
