"""Completion tests — Phases 3–5 remaining features."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.consistency_intelligence.discovery import DiscoveryContext, DiscoveryPipeline
from navigation.consistency_intelligence.discovery.sources.context7 import Context7KnowledgeSource
from navigation.consistency_intelligence.discovery.sources.figma import FigmaKnowledgeSource
from navigation.consistency_intelligence.discovery.sources.user_corrections import UserCorrectionsKnowledgeSource
from navigation.consistency_intelligence.graph.model import TokenNode, empty_graph
from navigation.consistency_intelligence.graph.persistence import GraphStore
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.service import ConsistencyIntelligenceService
from navigation.design_snapshot_engine import DesignSnapshotEngine

FIXTURE = {
	'url': 'http://localhost:5173/app',
	'viewport': {'width': 1280, 'height': 720},
	'document': {'scrollWidth': 1280, 'scrollHeight': 900},
	'css_variables': {'--brand': '#111827'},
	'elements': [
		{
			'tag': 'button',
			'selector': 'button.cta',
			'text': 'Buy',
			'classes': ['cta'],
			'style': {'padding': '14px', 'fontSize': '14px', 'color': 'var(--brand)'},
		},
	],
}


def test_batch_audit_finds_deviations() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		service = ConsistencyIntelligenceService(repo_root=root)
		snapshot = DesignSnapshotEngine().capture_from_fixture(FIXTURE)
		asyncio.run(
			service.refresh_graph(
				project_id='audit_test',
				design_snapshot=snapshot,
				enabled_sources=frozenset({'snapshot'}),
			)
		)
		detail = service.audit_snapshot_detail(snapshot, project_id='audit_test')
		assert detail['elements_audited'] >= 1
		assert 'grouped_findings' in detail


def test_component_similar_query() -> None:
	api = KnowledgeAPI()
	graph = empty_graph('sim_test')
	from navigation.consistency_intelligence.graph.model import ComponentNode

	graph.components['button'] = ComponentNode(name='button', variants=['primary', 'secondary'], confidence=0.9)
	graph.components['btn'] = ComponentNode(name='btn', variants=['primary'], confidence=0.8)
	api.save_graph(graph)

	resp = api.query('component.similar', {'component': 'button'}, project_id='sim_test')
	assert resp.answer['status'] == 'ok'
	assert resp.answer.get('similar')


def test_tokens_unused_and_fragmentation() -> None:
	api = KnowledgeAPI()
	graph = empty_graph('tok_test')
	graph.foundations.color_tokens = [
		TokenNode(path=('color', 'brand'), value='#111', provenance='declared', confidence=1.0),
		TokenNode(path=('color', 'accent'), value='#111', provenance='declared', confidence=1.0),
		TokenNode(path=('color', 'unused'), value='#222', provenance='declared', confidence=1.0),
	]
	from navigation.consistency_intelligence.graph.model import RelationshipEdge

	graph.relationships.append(RelationshipEdge(kind='uses_token', source='button', target='color.brand'))
	api.save_graph(graph)

	unused = api.query('tokens.unused', project_id='tok_test')
	assert unused.answer['count'] >= 1

	frag = api.query('tokens.fragmentation', project_id='tok_test')
	assert frag.answer['fragmentation_count'] >= 1


def test_graph_diff_with_history() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		store = GraphStore(storage_root=root)
		g1 = empty_graph('diff_test', repo_root=str(root))
		store.save(g1)
		v1 = g1.meta.graph_version.replace(':', '-')
		g2 = empty_graph('diff_test', repo_root=str(root))
		from navigation.consistency_intelligence.graph.model import ComponentNode

		g2.components['button'] = ComponentNode(name='button', confidence=0.9)
		store.save(g2)

		api = KnowledgeAPI(store)
		resp = api.query(
			'graph.diff',
			{'other_version': v1, 'repo_root': str(root)},
			project_id='diff_test',
		)
		assert resp.answer.get('status') == 'ok', resp.answer
		assert 'button' in (resp.answer.get('components_added') or [])


def test_extended_sources_via_options() -> None:
	graph = empty_graph('ext_test')
	ctx = DiscoveryContext(
		project_id='ext_test',
		enabled_sources=frozenset({'figma', 'context7', 'user_corrections'}),
		options={
			'figma_tokens': [{'path': 'color.primary', 'value': '#2563eb', 'type': 'color'}],
			'context7_conventions': [
				{'context': 'button', 'property': 'padding', 'expected_values': ['12px']},
			],
			'user_corrections': [
				{
					'standard_id': 'std_button_padding',
					'element_pattern': '.legacy',
					'actual_value': '10px',
					'rationale': 'approved legacy',
				},
			],
		},
	)
	pipeline = DiscoveryPipeline([
		FigmaKnowledgeSource(),
		Context7KnowledgeSource(),
		UserCorrectionsKnowledgeSource(),
	])
	graph, _, stats = asyncio.run(pipeline.run(ctx, graph))
	assert 'figma' in stats.sources_merged
	assert graph.foundations.color_tokens or graph.exceptions


def test_component_guidance_uses_graph() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		service = ConsistencyIntelligenceService(repo_root=root)
		snapshot = DesignSnapshotEngine().capture_from_fixture(FIXTURE)
		asyncio.run(
			service.refresh_graph(
				project_id='default',
				design_snapshot=snapshot,
				enabled_sources=frozenset({'snapshot'}),
			)
		)
		from navigation.component_intelligence.models import ComponentCandidate
		from navigation.consistency_intelligence.component_guidance import evaluate_component

		guidance = evaluate_component(
			ComponentCandidate(
				id='btn-1',
				provider='local',
				provider_group='local',
				name='button',
				title='Button',
				category='primitive',
				description='Button component',
				source='local',
			),
			repo_root=root,
		)
		assert guidance.spacing_adjustments or guidance.required_modifications or guidance.token_adjustments
		assert 'consistency_guidance_scaffold' not in guidance.degraded


def test_snapshot_extraction_gate() -> None:
	from navigation.consistency_intelligence.benchmark.snapshot_gate import snapshot_extraction_gate

	snapshot = DesignSnapshotEngine().capture_from_fixture(FIXTURE)
	gate = snapshot_extraction_gate(snapshot)
	assert gate['extraction_ok'] is True


def main() -> int:
	test_batch_audit_finds_deviations()
	test_component_similar_query()
	test_tokens_unused_and_fragmentation()
	test_graph_diff_with_history()
	test_extended_sources_via_options()
	test_component_guidance_uses_graph()
	test_snapshot_extraction_gate()
	print('consistency intelligence completion: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
