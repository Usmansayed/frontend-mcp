"""Phase 2 — Discovery Pipeline: sources, merge, refresh."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.consistency_intelligence.discovery import DiscoveryContext, DiscoveryPipeline, merge_fragments
from navigation.consistency_intelligence.discovery.sources.codebase import CodebaseKnowledgeSource
from navigation.consistency_intelligence.discovery.sources.snapshot import SnapshotKnowledgeSource
from navigation.consistency_intelligence.discovery.sources.tokens import TokensKnowledgeSource
from navigation.consistency_intelligence.graph.model import ComponentNode, StandardNode, TokenNode, empty_graph
from navigation.consistency_intelligence.graph.persistence import GraphStore
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.service import ConsistencyIntelligenceService
from navigation.design_snapshot_engine import DesignSnapshotEngine

FIXTURE = {
	'url': 'http://localhost:5173/login',
	'viewport': {'width': 1280, 'height': 720},
	'document': {'scrollWidth': 1280, 'scrollHeight': 900},
	'css_variables': {'--primary': '#2563eb', '--spacing-4': '16px'},
	'elements': [
		{
			'tag': 'button',
			'selector': 'button.primary',
			'text': 'Continue',
			'classes': ['primary'],
			'style': {
				'fontSize': '13px',
				'padding': '11px',
				'borderRadius': '5px',
			},
		},
	],
}


def _make_snapshot():
	engine = DesignSnapshotEngine()
	return engine.capture_from_fixture(FIXTURE)


def test_snapshot_source_extracts_components_and_standards() -> None:
	snapshot = _make_snapshot()
	ctx = DiscoveryContext(design_snapshot=snapshot, enabled_sources=frozenset({'snapshot'}))
	fragment = asyncio.run(SnapshotKnowledgeSource().collect(ctx))
	assert fragment.source_id == 'snapshot'
	assert fragment.components
	assert 'button' in fragment.components
	assert fragment.standards
	assert fragment.confidence > 0
	assert 'snapshot_missing' not in ' '.join(fragment.degraded)


def test_tokens_source_reads_dtcg_and_css() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / 'tokens.json').write_text(
			json.dumps({
				'color': {
					'primary': {'$value': '#2563eb', '$type': 'color'},
				},
				'spacing': {
					'4': {'$value': '16px', '$type': 'dimension'},
				},
			}),
			encoding='utf-8',
		)
		(root / 'globals.css').write_text(':root { --brand: #111827; --gap-md: 12px; }\n', encoding='utf-8')
		ctx = DiscoveryContext(repo_root=root, enabled_sources=frozenset({'tokens'}))
		fragment = asyncio.run(TokensKnowledgeSource().collect(ctx))
		assert len(fragment.tokens) >= 3
		assert any(t.provenance == 'declared' for t in fragment.tokens)
		assert fragment.confidence == 1.0


def test_codebase_source_finds_react_components() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		components_dir = root / 'src' / 'components'
		components_dir.mkdir(parents=True)
		(components_dir / 'Button.tsx').write_text(
			'export function Button({ variant = "primary" }) { return <button /> }\n',
			encoding='utf-8',
		)
		ctx = DiscoveryContext(repo_root=root, enabled_sources=frozenset({'codebase'}))
		fragment = asyncio.run(CodebaseKnowledgeSource().collect(ctx))
		assert 'button' in fragment.components
		assert fragment.components['button'].support_count >= 1


def test_merge_fragments_incremental() -> None:
	graph = empty_graph('merge_test')
	fragment = asyncio.run(
		SnapshotKnowledgeSource().collect(DiscoveryContext(design_snapshot=_make_snapshot()))
	)
	graph, stats = merge_fragments(graph, [fragment])
	assert stats.sources_merged == ['snapshot']
	assert stats.snapshot_ingested is True
	assert graph.meta.snapshot_count == 1
	assert graph.components
	assert graph.foundations.standards or graph.components['button'].standards

	# Second merge should increment snapshot count
	prev_count = graph.meta.snapshot_count
	graph, stats2 = merge_fragments(graph, [fragment])
	assert graph.meta.snapshot_count == prev_count + 1


def test_merge_declared_token_wins_over_learned() -> None:
	graph = empty_graph('token_merge')
	learned = TokenNode(
		path=('color', 'primary'),
		value='#ff0000',
		provenance='learned',
		confidence=0.7,
	)
	declared = TokenNode(
		path=('color', 'primary'),
		value='#2563eb',
		provenance='declared',
		confidence=1.0,
	)
	from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment

	graph, _ = merge_fragments(graph, [
		KnowledgeFragment(source_id='snapshot', tokens=[learned]),
		KnowledgeFragment(source_id='tokens', tokens=[declared]),
	])
	match = next(t for t in graph.foundations.color_tokens if t.path_str == 'color.primary')
	assert match.value == '#2563eb'
	assert match.provenance == 'declared'


def test_pipeline_end_to_end() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / 'tokens.json').write_text(
			json.dumps({'color': {'accent': {'$value': '#10b981', '$type': 'color'}}}),
			encoding='utf-8',
		)
		graph = empty_graph('pipeline_e2e', repo_root=str(root))
		ctx = DiscoveryContext(
			repo_root=root,
			design_snapshot=_make_snapshot(),
			enabled_sources=frozenset({'snapshot', 'tokens'}),
		)
		pipeline = DiscoveryPipeline([SnapshotKnowledgeSource(), TokensKnowledgeSource()])
		graph, degraded, stats = asyncio.run(pipeline.run(ctx, graph))
		assert stats.sources_merged
		assert 'discovery_pipeline_phase2_not_implemented' not in degraded
		assert graph.components
		assert graph.meta.snapshot_count == 1


def test_service_refresh_graph_persists() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		service = ConsistencyIntelligenceService(repo_root=root)
		snapshot = _make_snapshot()
		graph, degraded, stats = asyncio.run(
			service.refresh_graph(
				project_id='localhost_login',
				design_snapshot=snapshot,
				enabled_sources=frozenset({'snapshot'}),
			)
		)
		assert stats.snapshot_ingested
		path = root / '.perception' / 'design_graph_localhost_login.json'
		assert path.is_file()

		loaded = service.load_graph('localhost_login')
		assert loaded.meta.snapshot_count == 1
		assert loaded.components


def test_knowledge_queries_live_after_refresh() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		service = ConsistencyIntelligenceService(repo_root=root)
		asyncio.run(
			service.refresh_graph(
				project_id='knowledge_live',
				design_snapshot=_make_snapshot(),
				enabled_sources=frozenset({'snapshot'}),
			)
		)
		resp = service.query('graph.summary', project_id='knowledge_live')
		assert resp.answer['stats']['component_count'] > 0
		assert 'graph_empty' not in resp.degraded

		variants = service.query('component.variants', {'component': 'button'}, project_id='knowledge_live')
		assert variants.answer['status'] == 'ok'


def test_discovery_pipeline_stub_updated() -> None:
	graph = empty_graph('pipeline_test')
	ctx = DiscoveryContext(project_id='pipeline_test', enabled_sources=frozenset({'snapshot'}))
	pipeline = DiscoveryPipeline([SnapshotKnowledgeSource()])
	updated, degraded, stats = asyncio.run(pipeline.run(ctx, graph))
	assert 'discovery_pipeline_phase2_not_implemented' not in degraded
	assert 'snapshot_missing' in ' '.join(degraded)


def main() -> int:
	test_snapshot_source_extracts_components_and_standards()
	test_tokens_source_reads_dtcg_and_css()
	test_codebase_source_finds_react_components()
	test_merge_fragments_incremental()
	test_merge_declared_token_wins_over_learned()
	test_pipeline_end_to_end()
	test_service_refresh_graph_persists()
	test_knowledge_queries_live_after_refresh()
	test_discovery_pipeline_stub_updated()
	print('consistency intelligence phase 2: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
