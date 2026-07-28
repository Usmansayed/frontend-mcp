"""Parallel provider discovery wave."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.asyncio
async def test_provider_wave_runs_parallel_for_multiple_queries() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.models import InspirationCandidate
	from navigation.inspiration_intelligence.multi_scout import MultiScoutResult

	discover_calls: list[str] = []

	async def fake_discover(registry, provider_ids, **kwargs):
		q = kwargs['search_plan'].seed_query
		discover_calls.append(q)
		await asyncio.sleep(0.05)
		c = InspirationCandidate(
			provider_id='onepagelove',
			candidate_id=f'opl:{q[:12]}',
			title=f'Hit {q[:20]}',
			url='https://onepagelove.com/x',
			preview_ref='https://cdn.example.com/a.jpg',
		)
		return {'onepagelove': ([c], [])}, [{'provider_id': 'onepagelove', 'ok': True}], ['onepagelove']

	async def noop_multi(**kwargs):
		return MultiScoutResult(query='', scout_ms=0, probed=0, acquired=[])

	registry = type('R', (), {'get': lambda self, pid: None})()
	with patch(
		'navigation.inspiration_intelligence.collect.InspirationProviderRegistry',
		return_value=registry,
	):
		with patch(
			'navigation.inspiration_intelligence.collect.discover_providers_concurrent',
			side_effect=fake_discover,
		):
			with patch(
				'navigation.inspiration_intelligence.collect.multi_source_inspire_parallel',
				side_effect=noop_multi,
			):
				with patch(
					'navigation.inspiration_intelligence.collect.multi_source_inspire',
					side_effect=noop_multi,
				):
					with patch(
						'navigation.inspiration_intelligence.collect.acquire_pattern_inspiration',
						new_callable=AsyncMock,
						return_value=type('PR', (), {'to_dict': lambda s: {}, 'hits': [], 'targets': [], 'font_route': None, 'elapsed_ms': 0})(),
					):
						with patch('navigation.inspiration_intelligence.collect.InspirationBlobStore') as blob_cls:
							blob_cls.return_value.create_session.return_value = 'sess_pw'
							blob_cls.return_value.materialize_hits_async = AsyncMock(
								return_value={'materialized': 0}
							)
							manifest = await collect_inspiration_hits(
								'login signup form with email password',
								provider_ids=['onepagelove'],
								inspiration_level='standard',
								include_live_sites=False,
								include_web_search=False,
								max_web_screenshots=0,
								materialize_blobs=False,
								use_result_cache=False,
								write_per_hit_files=False,
								use_multi_scout=False,
								min_refs=1,
								target_refs=3,
							)

	parallel = manifest.get('parallel_queries') or []
	assert len(parallel) >= 2
	assert len(discover_calls) >= 2
	assert len(set(discover_calls)) >= 2
