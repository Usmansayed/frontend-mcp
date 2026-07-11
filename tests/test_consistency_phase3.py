"""Phase 3 — thin validator consumers (query graph only)."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.consistency_intelligence.consumers import ConsistencyValidator, FixProposer
from navigation.consistency_intelligence.graph.model import ComponentNode, StandardNode, empty_graph
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.service import ConsistencyIntelligenceService
from navigation.design_snapshot_engine import DesignSnapshotEngine

FIXTURE = {
	'url': 'http://localhost:5173/login',
	'viewport': {'width': 1280, 'height': 720},
	'document': {'scrollWidth': 1280, 'scrollHeight': 900},
	'css_variables': {},
	'elements': [
		{
			'tag': 'button',
			'selector': 'button.primary',
			'text': 'Go',
			'classes': ['primary'],
			'style': {'fontSize': '14px', 'padding': '12px', 'borderRadius': '8px'},
		},
	],
}


def _seed_graph(api: KnowledgeAPI, project_id: str = 'phase3_test') -> None:
	graph = empty_graph(project_id)
	graph.components['button'] = ComponentNode(
		name='button',
		variants=['primary', 'secondary'],
		standards=[
			StandardNode(
				id='std_button_padding',
				category='spacing',
				context='button',
				property='padding',
				expected_values=['12px', '16px'],
				distribution={'12px': 0.7, '16px': 0.3},
				confidence=0.92,
				support_count=47,
			),
			StandardNode(
				id='std_button_border-radius',
				category='radius',
				context='button',
				property='border-radius',
				expected_values=['8px'],
				confidence=0.88,
				support_count=40,
			),
		],
		confidence=0.9,
	)
	api.save_graph(graph)


def test_consistency_assess_consistent() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	resp = api.query(
		'consistency.assess',
		{'selector': 'button.primary', 'actual': {'padding': '12px'}},
		project_id='phase3_test',
	)
	assert resp.answer['status'] == 'ok'
	assert resp.answer['consistent'] is True
	assert resp.answer['deviation_count'] == 0


def test_consistency_assess_deviation() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	resp = api.query(
		'consistency.assess',
		{'selector': 'button.checkout', 'actual': {'padding': '13px', 'border-radius': '5px'}},
		project_id='phase3_test',
	)
	assert resp.answer['consistent'] is False
	assert len(resp.answer['deviations']) == 2


def test_consistency_explain_with_recommendation() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	resp = api.query(
		'consistency.explain',
		{'selector': 'button.checkout', 'actual': {'padding': '13px'}},
		project_id='phase3_test',
	)
	assert resp.recommendation is not None
	assert resp.recommendation.suggested_values.get('padding') == '12px'
	assert resp.standards


def test_fix_recommend() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	resp = api.query(
		'fix.recommend',
		{'standard_id': 'std_button_padding', 'selector': 'button.checkout', 'actual': {'padding': '13px'}},
		project_id='phase3_test',
	)
	assert resp.answer['status'] == 'ok'
	assert resp.recommendation is not None
	assert resp.recommendation.suggested_values['padding'] == '12px'


def test_validator_consumer_no_owned_state() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	validator = ConsistencyValidator(api)
	assess, explain = validator.assess_with_explanation(
		selector='button.checkout',
		actual={'padding': '13px'},
		project_id='phase3_test',
	)
	assert assess.answer['consistent'] is False
	assert explain is not None
	report = validator.to_report(assess, explain)
	assert report.passed is False
	assert report.findings


def test_fix_proposer_consumer() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	proposer = FixProposer(api)
	resp = proposer.recommend(
		standard_id='std_button_border-radius',
		selector='button.legacy',
		actual={'border-radius': '5px'},
		project_id='phase3_test',
	)
	assert proposer.recommendation(resp) is not None


def test_service_assess_after_refresh() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		service = ConsistencyIntelligenceService(repo_root=root)
		snapshot = DesignSnapshotEngine().capture_from_fixture(FIXTURE)
		asyncio.run(
			service.refresh_graph(
				project_id='refresh_assess',
				design_snapshot=snapshot,
				enabled_sources=frozenset({'snapshot'}),
			)
		)
		report = service.assess_consistency(
			selector='button.primary',
			actual={'padding': '99px'},
			project_id='refresh_assess',
		)
		assert isinstance(report.passed, bool)


def test_validator_does_not_mutate_graph() -> None:
	api = KnowledgeAPI()
	_seed_graph(api)
	before = api.load_graph('phase3_test').to_dict()
	validator = ConsistencyValidator(api)
	validator.assess_with_explanation(
		selector='button.x',
		actual={'padding': '1px'},
		project_id='phase3_test',
	)
	after = api.load_graph('phase3_test').to_dict()
	assert before == after


def main() -> int:
	test_consistency_assess_consistent()
	test_consistency_assess_deviation()
	test_consistency_explain_with_recommendation()
	test_fix_recommend()
	test_validator_consumer_no_owned_state()
	test_fix_proposer_consumer()
	test_service_assess_after_refresh()
	test_validator_does_not_mutate_graph()
	print('consistency intelligence phase 3: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
