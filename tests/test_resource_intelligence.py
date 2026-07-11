"""Resource Intelligence tests."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.resource_intelligence import ResourceDiscoveryRequest, ResourceIntelligenceService
from navigation.resource_intelligence.collect import collect_resource_assets
from navigation.resource_intelligence.license.policy import allows_use
from navigation.resource_intelligence.models import LicenseProfile, ResourceCategory
from navigation.resource_intelligence.tools.blob_store import ResourceBlobStore


def test_service_status_mvp() -> None:
	service = ResourceIntelligenceService()
	status = service.status()
	assert status['module'] == 'resource_intelligence'
	assert status['phase'] == 'production_v2'
	assert 'fontsource' in status['providers_live']
	assert 'pexels' in status['providers_live']
	assert 'open-doodles' in status['providers_live']
	assert 'pixabay' in status['providers_live']
	assert 'uigradients' in status['providers_live']
	assert '3dicons' in status['providers_live']
	assert 'rive' in status['providers_live']
	assert 'svg-repo' in status['providers_live']
	assert 'poly-pizza' in status['providers_live']


def test_license_summary_structure() -> None:
	from navigation.resource_intelligence.license.resolver import build_license_summary
	from navigation.resource_intelligence.models import LicenseProfile, ResourceDiscoveryRequest

	profile = LicenseProfile(spdx_id='MIT', commercial_use=True, attribution_required=False, mcp_download_allowed=True)
	summary = build_license_summary(profile, ResourceDiscoveryRequest(query='test'))
	d = summary.to_dict()
	assert 'commercial_use' in d
	assert 'requires_attribution' in d
	assert 'blocked_reason' in d
	assert d['allowed'] is True


def test_graph_store_persists() -> None:
	import tempfile
	from pathlib import Path

	from navigation.resource_intelligence.graph.store import ResourceGraphStore
	from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory

	with tempfile.TemporaryDirectory() as tmp:
		path = Path(tmp) / 'graph.json'
		store = ResourceGraphStore(path=path)
		store.upsert_asset(
			ResourceAssetRef(
				resource_id='lucide:settings',
				provider_id='lucide',
				category=ResourceCategory.ICON,
				title='Settings',
			)
		)
		store.save()
		store2 = ResourceGraphStore(path=path)
		assert store2.load()['assets']['lucide:settings']['title'] == 'Settings'


def test_commercial_providers_include_automation_restricted() -> None:
	service = ResourceIntelligenceService()
	providers = service.list_providers()
	ids = {p['provider_id'] for p in providers}
	assert 'fontsource' in ids
	assert 'undraw' in ids
	assert 'storyset' in ids
	assert 'humaaans' not in ids


def test_excluded_list_is_non_commercial_only() -> None:
	service = ResourceIntelligenceService()
	excluded = {p['provider_id'] for p in service.list_excluded_providers()}
	assert 'humaaans' in excluded
	assert 'undraw' not in excluded


def test_license_policy_allows_automation_restricted_commercial() -> None:
	profile = LicenseProfile(
		spdx_id='Custom',
		commercial_use=True,
		api_automation_allowed=False,
		mcp_download_allowed=False,
	)
	request = ResourceDiscoveryRequest(query='illustration', commercial_required=True)
	ok, reason = allows_use(profile, request)
	assert ok
	assert reason == ''


def test_license_policy_blocks_non_commercial() -> None:
	profile = LicenseProfile(spdx_id='CC-BY-NC', commercial_use=False)
	request = ResourceDiscoveryRequest(query='icon', commercial_required=True)
	ok, reason = allows_use(profile, request)
	assert not ok
	assert reason == 'commercial_use_denied'


def test_resource_guide_resource_readable() -> None:
	from navigation.mcp.resources import read_resource

	mime, payload, is_blob = read_resource('perception://resource-guide')
	assert mime == 'text/markdown'
	assert 'perception_resource_search' in payload
	assert not is_blob


def test_blob_store_session_lifecycle() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp) / 'blobs'
		sessions = Path(tmp) / 'sessions.json'
		with patch.dict(
			'os.environ',
			{
				'RESOURCE_BLOB_ROOT': str(root),
				'RESOURCE_SESSIONS_CACHE': str(sessions),
			},
		):
			store = ResourceBlobStore()
			session_id = store.create_session(purpose='test')
			assert session_id.startswith('res_')

			# minimal valid 1x1 PNG
			png = bytes.fromhex(
				'89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
				'0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082'
			)
			hits = [
				{
					'resource_id': 'test:icon',
					'provider_id': 'iconify',
					'title': 'Test Icon',
					'preview_url': 'https://example.com/icon.png',
					'access_url': 'https://example.com/icon.svg',
					'format': 'png',
				}
			]
			with patch.object(store, '_fetch_bytes', return_value=png):
				summary = store.materialize_hits(session_id, hits)
			assert summary['materialized'] == 1
			assert hits[0]['resource_blob']
			assert Path(hits[0]['resource_blob']).is_file()

			removed = store.end_session(session_id)
			assert removed == 1
			assert not (root / session_id).exists()


def test_search_iconify_live() -> None:
	async def _run() -> None:
		service = ResourceIntelligenceService()
		result = await service.search(
			ResourceDiscoveryRequest(
				query='settings gear icon',
				categories=[ResourceCategory.ICON],
				max_results=5,
				provider_preference='iconify',
				icon_family=None,
			)
		)
		assert 'iconify' in result.providers_queried
		assert result.assets
		assert result.assets[0].access_url.startswith('https://')

	asyncio.run(_run())


def test_search_icon_family_lucide() -> None:
	async def _run() -> None:
		service = ResourceIntelligenceService()
		result = await service.search(
			ResourceDiscoveryRequest(
				query='settings icon',
				categories=[ResourceCategory.ICON],
				max_results=3,
				icon_family='lucide',
			)
		)
		assert result.icon_family == 'lucide'
		assert result.family_match is True
		assert result.assets
		assert all(a.metadata.get('family_match') for a in result.assets)
		assert all('lucide' in a.resource_id for a in result.assets)

	asyncio.run(_run())


def test_collect_skips_blobs_for_family_icons() -> None:
	async def _run() -> None:
		with tempfile.TemporaryDirectory() as tmp:
			with patch.dict(
				'os.environ',
				{
					'RESOURCE_BLOB_ROOT': str(Path(tmp) / 'blobs'),
					'RESOURCE_SESSIONS_CACHE': str(Path(tmp) / 'sessions.json'),
					'RESOURCE_BLOBS': '1',
				},
			):
				manifest = await collect_resource_assets(
					'settings icon',
					max_results=2,
					icon_family='lucide',
					materialize_blobs=True,
					blob_fallback_only=True,
				)
				assert manifest.get('family_match') is True
				hits = manifest['hits']
				assert hits
				assert all(h.get('blob_skipped') for h in hits)
				assert not manifest.get('blob_session_id')

	asyncio.run(_run())


def test_collect_preview_materializes_blobs_for_avatars() -> None:
	async def _run() -> None:
		with tempfile.TemporaryDirectory() as tmp:
			with patch.dict(
				'os.environ',
				{
					'RESOURCE_BLOB_ROOT': str(Path(tmp) / 'blobs'),
					'RESOURCE_SESSIONS_CACHE': str(Path(tmp) / 'sessions.json'),
					'RESOURCE_BLOBS': '1',
				},
			):
				manifest = await collect_resource_assets(
					'user avatar',
					max_results=1,
					categories=['avatar'],
					provider_preference='dicebear',
					materialize_blobs=True,
				)
				assert manifest['total_hits'] >= 1
				hits = manifest['hits']
				assert manifest.get('blob_session_id', '').startswith('res_')
				assert any(h.get('resource_blob') for h in hits)

	asyncio.run(_run())


def test_uigradients_search() -> None:
	async def _run() -> None:
		from navigation.resource_intelligence.providers.uigradients.provider import UiGradientsProvider

		provider = UiGradientsProvider()
		assets, _deg = await provider.search('purple gradient', category=ResourceCategory.GRADIENT, max_results=3)
		assert assets
		assert assets[0].provider_id == 'uigradients'
		assert 'css' in assets[0].metadata

	asyncio.run(_run())


def test_threedicons_search() -> None:
	async def _run() -> None:
		from navigation.resource_intelligence.providers.threedicons.provider import ThreeDiconsProvider

		provider = ThreeDiconsProvider()
		assets, _deg = await provider.search('rocket launch', category=ResourceCategory.THREE_D, max_results=2)
		assert assets
		assert any('rocket' in a.resource_id for a in assets)

	asyncio.run(_run())


def test_rive_metadata_search() -> None:
	async def _run() -> None:
		from navigation.resource_intelligence.providers.rive.provider import RiveProvider

		provider = RiveProvider()
		assets, deg = await provider.search('loading spinner', category=ResourceCategory.ANIMATION, max_results=2)
		assert assets
		assert any('rive_metadata_only' in d for d in deg)
		assert assets[0].metadata.get('no_public_cdn') is True

	asyncio.run(_run())


def test_svg_repo_requires_api_key() -> None:
	async def _run() -> None:
		from navigation.resource_intelligence.providers.svg_repo.provider import SvgRepoProvider

		with patch.dict('os.environ', {}, clear=False):
			os.environ.pop('SVG_REPO_API_KEY', None)
			os.environ.pop('SVGAPI_DOMAIN_KEY', None)
			provider = SvgRepoProvider()
			assets, deg = await provider.search('settings', category=ResourceCategory.SVG, max_results=2)
			assert not assets
			assert any('svg_repo_api_key_missing' in d for d in deg)

	asyncio.run(_run())


def test_orchestrator_gradient_category() -> None:
	async def _run() -> None:
		from navigation.resource_intelligence.planning.orchestrator import ResourceSearchOrchestrator

		orch = ResourceSearchOrchestrator()
		result = await orch.search(
			ResourceDiscoveryRequest(
				query='purple saas gradient',
				categories=[ResourceCategory.GRADIENT],
				max_results=3,
			)
		)
		assert result.assets
		assert 'uigradients' in result.providers_queried

	asyncio.run(_run())
