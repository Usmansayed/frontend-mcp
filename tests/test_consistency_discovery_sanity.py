"""Pre-Phase-3 sanity checks — Discovery Pipeline freeze gate."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.consistency_intelligence.discovery import DiscoveryContext, DiscoveryPipeline, merge_fragments
from navigation.consistency_intelligence.discovery.sources.codebase import CodebaseKnowledgeSource
from navigation.consistency_intelligence.discovery.sources.snapshot import SnapshotKnowledgeSource
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.discovery.sources.tokens import TokensKnowledgeSource
from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	ProjectDesignGraph,
	StandardNode,
	TokenNode,
	empty_graph,
)
from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.design_snapshot_engine import DesignSnapshotEngine

FIXTURE = {
	'url': 'http://localhost:5173/dashboard',
	'viewport': {'width': 1280, 'height': 720},
	'document': {'scrollWidth': 1280, 'scrollHeight': 900},
	'css_variables': {'--primary': '#2563eb'},
	'elements': [
		{
			'tag': 'button',
			'selector': 'button.primary',
			'text': 'Save',
			'classes': ['primary'],
			'style': {'fontSize': '14px', 'padding': '12px', 'borderRadius': '8px'},
		},
		{
			'tag': 'button',
			'selector': 'button.secondary',
			'text': 'Cancel',
			'classes': ['secondary'],
			'style': {'fontSize': '14px', 'padding': '12px', 'borderRadius': '8px'},
		},
	],
}

# Latency budget per query on a 10k-component graph (milliseconds)
LATENCY_BUDGET_MS = {
	'graph.summary': 150.0,
	'standard.for_context': 50.0,
	'component.variants': 30.0,
	'component.canonical': 30.0,
	'confidence.for': 30.0,
}


def _snapshot():
	return DesignSnapshotEngine().capture_from_fixture(FIXTURE)


def _pipeline(sources=None):
	return DiscoveryPipeline(sources or [
		SnapshotKnowledgeSource(),
		CodebaseKnowledgeSource(),
		TokensKnowledgeSource(),
	])


def test_graph_grows_over_multiple_refreshes() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(src := root / 'src' / 'components').mkdir(parents=True)
		(src / 'Button.tsx').write_text('export function Button() {}\n', encoding='utf-8')
		(root / 'tokens.json').write_text(
			json.dumps({'color': {'brand': {'$value': '#111827', '$type': 'color'}}}),
			encoding='utf-8',
		)

		graph = empty_graph('growth_test', repo_root=str(root))
		pipeline = _pipeline()
		counts: list[dict[str, int]] = []

		for _ in range(5):
			ctx = DiscoveryContext(
				repo_root=root,
				design_snapshot=_snapshot(),
				enabled_sources=frozenset({'snapshot', 'codebase', 'tokens'}),
			)
			graph, degraded, stats = asyncio.run(pipeline.run(ctx, graph))
			assert stats.sources_merged, f'expected merges, degraded={degraded}'
			counts.append({
				'snapshots': graph.meta.snapshot_count,
				'components': len(graph.components),
				'standards': len(graph.foundations.standards) + sum(len(c.standards) for c in graph.components.values()),
				'tokens': len(graph.foundations.color_tokens),
			})

		assert counts[-1]['snapshots'] == 5
		for i in range(1, len(counts)):
			assert counts[i]['snapshots'] == counts[i - 1]['snapshots'] + 1
			assert counts[i]['components'] >= counts[0]['components']
			assert counts[i]['tokens'] >= counts[0]['tokens']


def test_conflicting_sources_declared_beats_learned() -> None:
	graph = empty_graph('conflict_test')
	learned = TokenNode(
		path=('color', 'brand'),
		value='#ff0000',
		resolved_value='#ff0000',
		provenance='learned',
		confidence=0.95,
		source='snapshot',
	)
	declared = TokenNode(
		path=('color', 'brand'),
		value='#111827',
		resolved_value='#111827',
		provenance='declared',
		confidence=1.0,
		source='dtcg',
	)
	graph, _ = merge_fragments(graph, [
		KnowledgeFragment(source_id='snapshot', tokens=[learned], confidence=0.9),
		KnowledgeFragment(source_id='tokens', tokens=[declared], confidence=1.0),
	])
	token = next(t for t in graph.foundations.color_tokens if t.path_str == 'color.brand')
	assert token.value == '#111827'
	assert token.provenance == 'declared'

	# Re-merge learned should not overwrite declared
	graph, _ = merge_fragments(graph, [
		KnowledgeFragment(source_id='snapshot', tokens=[learned], confidence=0.99),
	])
	token = next(t for t in graph.foundations.color_tokens if t.path_str == 'color.brand')
	assert token.value == '#111827'
	assert token.provenance == 'declared'


def test_incremental_merge_does_not_corrupt_standards() -> None:
	graph = empty_graph('integrity_test')
	manual = StandardNode(
		id='std_button_padding',
		category='spacing',
		context='button',
		property='padding',
		expected_values=['16px'],
		distribution={'16px': 1.0},
		confidence=0.99,
		support_count=100,
		provenance='user',
	)
	graph.foundations.standards.append(manual)

	weaker = StandardNode(
		id='std_button_padding',
		category='spacing',
		context='button',
		property='padding',
		expected_values=['11px'],
		distribution={'11px': 1.0},
		confidence=0.6,
		support_count=1,
		provenance='learned',
	)
	graph, stats = merge_fragments(graph, [
		KnowledgeFragment(source_id='snapshot', standards=[weaker]),
	])
	merged = graph.find_standard('std_button_padding')
	assert merged is not None
	assert '16px' in merged.expected_values
	assert merged.support_count == 101
	assert merged.provenance == 'user'

	# Stronger incoming should update expected values
	stronger = StandardNode(
		id='std_button_padding',
		category='spacing',
		context='button',
		property='padding',
		expected_values=['20px'],
		distribution={'20px': 1.0},
		confidence=0.95,
		support_count=200,
		provenance='learned',
	)
	graph, _ = merge_fragments(graph, [KnowledgeFragment(source_id='snapshot', standards=[stronger])])
	merged = graph.find_standard('std_button_padding')
	assert merged is not None
	assert merged.expected_values[0] == '20px'
	assert merged.support_count == 301


def _build_large_graph(component_count: int = 10_000) -> ProjectDesignGraph:
	graph = empty_graph('perf_test')
	for i in range(component_count):
		name = f'widget_{i}'
		graph.components[name] = ComponentNode(
			name=name,
			variants=['primary', 'secondary'] if i % 3 == 0 else ['default'],
			states=['hover', 'focus'] if i % 5 == 0 else [],
			standards=[
				StandardNode(
					id=f'std_{name}_padding',
					category='spacing',
					context=name,
					property='padding',
					expected_values=['12px', '16px'],
					distribution={'12px': 0.6, '16px': 0.4},
					confidence=0.85,
					support_count=10,
				),
			] if i % 2 == 0 else [],
			support_count=5,
			confidence=0.8,
		)
	graph.foundations.standards.append(
		StandardNode(
			id='std_global_spacing',
			category='spacing',
			context='global',
			property='gap',
			expected_values=['8px'],
			confidence=0.9,
			support_count=500,
		)
	)
	return graph


def _time_ms(fn) -> float:
	start = time.perf_counter()
	fn()
	return (time.perf_counter() - start) * 1000.0


def test_query_latency_at_scale() -> None:
	graph = _build_large_graph(10_000)
	api = KnowledgeAPI()
	api.save_graph(graph)

	timings: dict[str, float] = {}
	timings['graph.summary'] = _time_ms(lambda: api.query('graph.summary', project_id='perf_test'))
	timings['standard.for_context'] = _time_ms(
		lambda: api.query('standard.for_context', {'context': 'widget_5000', 'property': 'padding'}, project_id='perf_test')
	)
	timings['component.variants'] = _time_ms(
		lambda: api.query('component.variants', {'component': 'widget_42'}, project_id='perf_test')
	)
	timings['component.canonical'] = _time_ms(
		lambda: api.query('component.canonical', {'component': 'widget_42'}, project_id='perf_test')
	)
	timings['confidence.for'] = _time_ms(
		lambda: api.query('confidence.for', {'standard_id': 'std_widget_100_padding'}, project_id='perf_test')
	)

	failures = [
		f'{qid}: {ms:.1f}ms > {LATENCY_BUDGET_MS[qid]}ms'
		for qid, ms in timings.items()
		if ms > LATENCY_BUDGET_MS[qid]
	]
	assert not failures, 'Latency budget exceeded:\n' + '\n'.join(failures)


def main() -> int:
	test_graph_grows_over_multiple_refreshes()
	test_conflicting_sources_declared_beats_learned()
	test_incremental_merge_does_not_corrupt_standards()
	test_query_latency_at_scale()
	print('discovery pipeline sanity checks: PASS')
	for qid, budget in LATENCY_BUDGET_MS.items():
		print(f'  {qid}: within {budget}ms budget')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
