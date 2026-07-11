"""Phase 1 — Project Design Graph + Knowledge API foundation tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	ProjectDesignGraph,
	StandardNode,
	empty_graph,
)
from navigation.consistency_intelligence.graph.persistence import GraphStore
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.knowledge.registry import QUERY_CATALOG
from navigation.consistency_intelligence.service import ConsistencyIntelligenceService


def test_empty_graph_roundtrip() -> None:
	graph = empty_graph('test_project', repo_root='/tmp/demo')
	data = graph.to_dict()
	restored = ProjectDesignGraph.from_dict(data)
	assert restored.meta.project_id == 'test_project'
	assert restored.meta.graph_version.startswith('pdg_')


def test_graph_persistence() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		store = GraphStore(storage_root=root)
		graph = empty_graph('persist_test', repo_root=str(root))
		graph.foundations.standards.append(
			StandardNode(
				id='std_card_padding',
				category='spacing',
				context='card',
				property='padding',
				expected_values=['16px'],
				confidence=0.9,
				support_count=10,
			)
		)
		store.save(graph)

		store2 = GraphStore(storage_root=root)
		loaded = store2.load('persist_test')
		assert len(loaded.foundations.standards) == 1
		assert loaded.foundations.standards[0].id == 'std_card_padding'


def test_knowledge_api_graph_summary() -> None:
	api = KnowledgeAPI()
	resp = api.summary(project_id='default')
	assert resp.query.query_id == 'graph.summary'
	assert resp.answer['status'] == 'ok'
	assert 'stats' in resp.answer
	assert resp.graph_version.startswith('pdg_')


def test_knowledge_api_standard_for_context_with_data() -> None:
	api = KnowledgeAPI()
	graph = empty_graph('ctx_test')
	graph.foundations.standards.append(
		StandardNode(
			id='std_button_pad',
			category='spacing',
			context='button',
			property='padding',
			expected_values=['16px'],
			confidence=0.95,
			support_count=20,
		)
	)
	api.save_graph(graph)

	resp = api.query(
		'standard.for_context',
		{'context': 'button', 'property': 'padding'},
		project_id='ctx_test',
	)
	assert resp.answer['status'] == 'ok'
	assert len(resp.standards) == 1
	assert resp.standards[0].expected_values == ['16px']
	assert resp.confidence == 0.95


def test_knowledge_api_stub_unknown_query() -> None:
	api = KnowledgeAPI()
	resp = api.query('not.a.real.query', {})
	assert 'unknown_query_id' in resp.degraded


def test_all_catalog_queries_registered() -> None:
	api = KnowledgeAPI()
	handlers = api._handlers
	for spec in QUERY_CATALOG:
		assert spec.query_id in handlers, f'missing handler for {spec.query_id}'


def test_component_variants_from_graph() -> None:
	api = KnowledgeAPI()
	graph = empty_graph('comp_test')
	graph.components['button'] = ComponentNode(
		name='button',
		variants=['primary', 'secondary', 'ghost'],
		states=['hover', 'focus'],
		confidence=0.88,
	)
	api.save_graph(graph)

	resp = api.query('component.variants', {'component': 'button'}, project_id='comp_test')
	assert resp.answer['variants'] == ['primary', 'secondary', 'ghost']


def test_service_list_queries() -> None:
	service = ConsistencyIntelligenceService()
	queries = service.list_queries()
	assert len(queries) == len(QUERY_CATALOG)
	assert any(q['query_id'] == 'graph.summary' for q in queries)


def test_service_audit_returns_knowledge_summary() -> None:
	service = ConsistencyIntelligenceService()

	class _Snap:
		url = 'http://localhost:5173/login'

	report = service.audit(_Snap())
	assert isinstance(report.passed, bool)
	assert 'graph_empty_run_refresh' in report.degraded or report.summary


def test_discovery_pipeline_stub() -> None:
	import asyncio
	from navigation.consistency_intelligence.discovery import DiscoveryContext, DiscoveryPipeline
	from navigation.consistency_intelligence.discovery.sources.snapshot import SnapshotKnowledgeSource
	from navigation.consistency_intelligence.graph.model import empty_graph

	graph = empty_graph('pipeline_test')
	ctx = DiscoveryContext(project_id='pipeline_test', enabled_sources=frozenset({'snapshot'}))
	pipeline = DiscoveryPipeline([SnapshotKnowledgeSource()])
	updated, degraded, stats = asyncio.run(pipeline.run(ctx, graph))
	assert 'discovery_pipeline_phase2_not_implemented' not in degraded
	assert 'snapshot_missing' in ' '.join(degraded)


def main() -> int:
	test_empty_graph_roundtrip()
	test_graph_persistence()
	test_knowledge_api_graph_summary()
	test_knowledge_api_standard_for_context_with_data()
	test_knowledge_api_stub_unknown_query()
	test_all_catalog_queries_registered()
	test_component_variants_from_graph()
	test_service_list_queries()
	test_service_audit_returns_knowledge_summary()
	test_discovery_pipeline_stub()
	print('consistency intelligence phase 1: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
