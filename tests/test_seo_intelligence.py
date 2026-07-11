"""SEO Intelligence tests — architecture phase."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence import SeoAuditRequest, SeoIntelligenceService
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditResult, SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.registry import SeoProviderRegistry


def test_service_status_production_phase() -> None:
	service = SeoIntelligenceService()
	status = service.status()
	assert status['module'] == 'seo_intelligence'
	assert status['phase'] == 'production_v1'
	assert 'search-console' in status['providers_live']
	assert 'keyword_databases' in status['do_not_build']
	assert 'integrations' in status


def test_provider_registry_free_first() -> None:
	registry = SeoProviderRegistry()
	providers = registry.list_providers()
	ids = {p['provider_id'] for p in providers}
	assert 'search-console' in ids
	assert 'openseo' in ids
	assert 'librecrawl' in ids
	free_core = [p for p in providers if p['provider_id'] in ('search-console', 'analytics-ga4', 'librecrawl', 'lighthouse')]
	assert all(p.get('free_tier') for p in free_core)
	openseo = next(p for p in providers if p['provider_id'] == 'openseo')
	assert openseo.get('free_tier') is False


def test_planner_prefers_gsc_over_openseo_for_keywords() -> None:
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', intents=['keyword_research'])
	route = planner.route_capability('keyword_research', request, {'search-console': 'connected'})
	assert route is not None
	assert route.chosen_provider == 'search-console'
	assert 'openseo' in ''.join(route.skipped_providers) or route.chosen_provider != 'openseo'


def test_planner_blocks_openseo_for_technical_crawl() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(
		website_url='https://example.com',
		intents=['technical_crawl'],
		allow_openseo=True,
		allow_paid_providers=True,
	)
	with patch.dict(
		'os.environ',
		{'OPENSEO_BASE_URL': 'http://localhost:3001', 'LIBRECRAWL_BASE_URL': 'http://localhost:8080'},
	):
		route = planner.route_capability(
			'technical_crawl',
			request,
			{'openseo': 'connected', 'librecrawl': 'connected'},
		)
	assert route is not None
	assert route.chosen_provider == 'librecrawl'


def test_planner_blocks_paid_openseo_without_flag() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(
		website_url='https://example.com',
		intents=['serp_analysis'],
		allow_paid_providers=False,
	)
	with patch.dict('os.environ', {'OPENSEO_BASE_URL': 'http://localhost:3001'}):
		route = planner.route_capability('serp_analysis', request, {'openseo': 'connected'})
	assert route is not None
	assert route.chosen_provider == ''
	assert any('paid' in s for s in route.skipped_providers)


def test_graph_store_persists() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		store = SeoKnowledgeGraphStore(path=Path(tmp) / 'seo_graph.json')
		store.set_website('https://example.com', property_url='sc-domain:example.com')
		store.upsert_evidence(
			SeoEvidenceRef(
				evidence_id='gsc:query:1',
				provider_id='search-console',
				kind=SeoEvidenceKind.SEARCH_QUERY,
				title='example query',
				summary='test',
			)
		)
		store.save()
		reloaded = SeoKnowledgeGraphStore(path=Path(tmp) / 'seo_graph.json')
		summary = reloaded.summary()
		assert summary['evidence_count'] == 1
		assert summary['website']['url'] == 'https://example.com'


def test_audit_returns_capability_routes() -> None:
	async def _run() -> None:
		service = SeoIntelligenceService()
		result = await service.audit(SeoAuditRequest(website_url='https://example.com'))
		assert result.capability_routes
		assert result.connections
		assert 'search-console' in result.connections

	asyncio.run(_run())


def test_audit_returns_connections_and_degraded() -> None:
	async def _run() -> None:
		service = SeoIntelligenceService()
		result = await service.audit(SeoAuditRequest(website_url='https://example.com'))
		assert result.connections
		assert 'search-console' in result.connections
		assert result.evidence or result.degraded
		assert result.graph_summary

	asyncio.run(_run())


def test_seo_guide_mcp_resource() -> None:
	from navigation.mcp.resources import read_resource

	mime, payload, is_blob = read_resource('perception://seo-guide')
	assert mime == 'text/markdown'
	assert 'perception_seo_audit' in payload
	assert not is_blob


def test_cross_analysis_requires_evidence_ids() -> None:
	from navigation.seo_intelligence.analysis.cross_analyzer import run_cross_analysis

	evidence = [
		SeoEvidenceRef(
			evidence_id='a1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Not indexed',
			summary='Page excluded',
			severity='high',
		),
		SeoEvidenceRef(
			evidence_id='b1',
			provider_id='browser',
			kind=SeoEvidenceKind.RENDERING_ISSUE,
			title='Hydration error',
			summary='Client render failed',
			severity='high',
		),
	]
	findings = run_cross_analysis(evidence)
	assert findings
	assert all(f.get('evidence_ids') for f in findings)


def test_openseo_not_configured_without_url() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.providers.openseo.provider import OpenSeoProvider

	async def _run() -> None:
		with patch.dict('os.environ', {}, clear=True):
			provider = OpenSeoProvider()
			status, degraded = await provider.connection_status(SeoAuditRequest(website_url='https://example.com'))
			assert status == 'not_configured'
			assert any('openseo_not_configured' in d for d in degraded)

	asyncio.run(_run())


def test_openseo_collect_search_queries_free() -> None:
	from unittest.mock import AsyncMock, MagicMock, patch

	from navigation.seo_intelligence.providers.openseo.provider import OpenSeoProvider

	mock_client = MagicMock()
	mock_client.configured.return_value = True
	mock_client.call_tool = AsyncMock(
		return_value=(
			{
				'ok': True,
				'siteUrl': 'https://example.com/',
				'rows': [
					{'keys': ['example query'], 'clicks': 10, 'impressions': 100, 'ctr': 0.1, 'position': 5.2},
				],
			},
			[],
		)
	)

	async def _run() -> None:
		with patch.dict(
			'os.environ',
			{'OPENSEO_BASE_URL': 'http://localhost:3001', 'OPENSEO_PROJECT_ID': 'proj-1'},
		):
			provider = OpenSeoProvider(client=mock_client)
			evidence, degraded = await provider.collect(
				SeoAuditRequest(website_url='https://example.com', allow_openseo=True),
				capabilities=['search_queries'],
			)
			assert len(evidence) == 1
			assert evidence[0].provider_id == 'openseo'
			assert evidence[0].kind == SeoEvidenceKind.SEARCH_QUERY
			mock_client.call_tool.assert_awaited_once()
			call_args = mock_client.call_tool.await_args
			assert call_args.args[0] == 'get_search_console_performance'

	asyncio.run(_run())


def test_openseo_collect_inspect_urls_free() -> None:
	from unittest.mock import AsyncMock, MagicMock, patch

	from navigation.seo_intelligence.providers.openseo.provider import OpenSeoProvider

	mock_client = MagicMock()
	mock_client.configured.return_value = True
	mock_client.call_tool = AsyncMock(
		return_value=(
			{
				'ok': True,
				'siteUrl': 'https://example.com/',
				'results': [
					{
						'url': 'https://example.com/',
						'result': {
							'indexStatusResult': {
								'verdict': 'PASS',
								'coverageState': 'Submitted and indexed',
							},
						},
					},
				],
			},
			[],
		)
	)

	async def _run() -> None:
		with patch.dict(
			'os.environ',
			{'OPENSEO_BASE_URL': 'http://localhost:3001', 'OPENSEO_PROJECT_ID': 'proj-1'},
		):
			provider = OpenSeoProvider(client=mock_client)
			evidence, degraded = await provider.collect(
				SeoAuditRequest(website_url='https://example.com', allow_openseo=True),
				capabilities=['index_status'],
			)
			assert len(evidence) == 1
			assert evidence[0].kind == SeoEvidenceKind.INDEX_STATUS
			call_args = mock_client.call_tool.await_args
			assert call_args.args[0] == 'inspect_urls'
			assert call_args.args[1]['urls'] == ['https://example.com']

	asyncio.run(_run())


def test_openseo_blocks_paid_capabilities() -> None:
	from unittest.mock import MagicMock, patch

	from navigation.seo_intelligence.providers.openseo.provider import OpenSeoProvider

	mock_client = MagicMock()
	mock_client.configured.return_value = True

	async def _run() -> None:
		with patch.dict(
			'os.environ',
			{'OPENSEO_BASE_URL': 'http://localhost:3001', 'OPENSEO_PROJECT_ID': 'proj-1'},
		):
			provider = OpenSeoProvider(client=mock_client)
			evidence, degraded = await provider.collect(
				SeoAuditRequest(
					website_url='https://example.com',
					allow_openseo=True,
					allow_paid_providers=False,
				),
				capabilities=['serp_analysis'],
			)
			assert not evidence
			assert any('paid_capabilities_blocked' in d for d in degraded)
			mock_client.call_tool.assert_not_called()

	asyncio.run(_run())


def test_openseo_paid_allowed_but_not_implemented() -> None:
	from unittest.mock import AsyncMock, MagicMock, patch

	from navigation.seo_intelligence.providers.openseo.provider import OpenSeoProvider

	mock_client = MagicMock()
	mock_client.configured.return_value = True
	mock_client.call_tool = AsyncMock(return_value=(None, []))

	async def _run() -> None:
		with patch.dict(
			'os.environ',
			{'OPENSEO_BASE_URL': 'http://localhost:3001', 'OPENSEO_PROJECT_ID': 'proj-1'},
		):
			provider = OpenSeoProvider(client=mock_client)
			evidence, degraded = await provider.collect(
				SeoAuditRequest(
					website_url='https://example.com',
					allow_openseo=True,
					allow_paid_providers=True,
				),
				capabilities=['keyword_research'],
			)
			assert not evidence
			assert any('paid_adapter_not_implemented' in d for d in degraded)
			mock_client.call_tool.assert_not_called()

	asyncio.run(_run())


def test_planner_routes_index_status_to_openseo_when_gsc_unavailable() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', intents=['index_status'], allow_openseo=True)
	with patch.dict('os.environ', {'OPENSEO_BASE_URL': 'http://localhost:3001'}):
		route = planner.route_capability(
			'index_status',
			request,
			{'search-console': 'not_configured', 'openseo': 'connected'},
		)
	assert route is not None
	assert route.chosen_provider == 'openseo'


def test_browser_bridge_from_scan_registry() -> None:
	from navigation.core.scan_registry import ScanRegistry
	from navigation.seo_intelligence.providers.browser.provider import BrowserSeoProvider

	scans = ScanRegistry()
	record = scans.register(
		session_id='s1',
		run_id='r1',
		url='https://example.com',
		observation={
			'url': 'https://example.com',
			'dev_insights': {
				'issues': [{'kind': 'exception', 'message': 'Hydration failed', 'tier': 'blocking'}],
			},
			'console': {'blocking': ['TypeError: undefined is not a function']},
		},
	)

	async def _run() -> None:
		provider = BrowserSeoProvider(scan_registry=scans)
		status, _ = await provider.connection_status(
			SeoAuditRequest(website_url='https://example.com', scan_id=record.scan_id)
		)
		assert status == 'connected'
		evidence, degraded = await provider.collect(
			SeoAuditRequest(website_url='https://example.com', scan_id=record.scan_id)
		)
		assert evidence
		assert any(e.kind == SeoEvidenceKind.RENDERING_ISSUE for e in evidence)
		assert not degraded or 'browser_no_seo_evidence' not in degraded

	asyncio.run(_run())


def test_cross_analysis_technical_index() -> None:
	from navigation.seo_intelligence.analysis.cross_analyzer import run_cross_analysis

	evidence = [
		SeoEvidenceRef(
			evidence_id='t1',
			provider_id='librecrawl',
			kind=SeoEvidenceKind.TECHNICAL_ISSUE,
			title='HTTP 404',
			summary='Not found',
			severity='high',
		),
		SeoEvidenceRef(
			evidence_id='i1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Not indexed',
			summary='Excluded',
			severity='high',
		),
	]
	findings = run_cross_analysis(evidence)
	assert any(f['analysis_id'] == 'technical_index_correlation' for f in findings)


def test_verification_passes_when_evidence_cleared() -> None:
	from navigation.seo_intelligence.models import SeoRecommendation
	from navigation.seo_intelligence.verification.loop import evaluate_verification

	baseline = SeoAuditResult(
		request=SeoAuditRequest(website_url='https://example.com'),
		evidence=[
			SeoEvidenceRef(
				evidence_id='e1',
				provider_id='lighthouse',
				kind=SeoEvidenceKind.CORE_WEB_VITAL,
				title='Poor LCP',
				summary='slow',
				severity='high',
			),
		],
		recommendations=[
			SeoRecommendation(
				recommendation_id='rec_e1',
				title='Fix LCP',
				summary='slow',
				priority='high',
				category='core_web_vital',
				evidence_ids=['e1'],
			),
		],
	)
	current = SeoAuditResult(
		request=SeoAuditRequest(website_url='https://example.com'),
		evidence=[],
		recommendations=[],
	)
	result = evaluate_verification(
		baseline=baseline,
		current=current,
		recommendation_ids=['rec_e1'],
	)
	assert result['passed_count'] == 1


def test_gsc_normalize_search_analytics() -> None:
	from navigation.seo_intelligence.providers.search_console.normalize import normalize_search_analytics

	evidence = normalize_search_analytics(
		{
			'rows': [
				{'keys': ['query'], 'clicks': 1, 'impressions': 10, 'ctr': 0.1, 'position': 3.0},
			],
		},
		site_url='https://example.com/',
	)
	assert len(evidence) == 1
	assert evidence[0].kind == SeoEvidenceKind.SEARCH_QUERY


def test_seo_connect_status() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.auth.google import google_oauth_status

	with patch.dict('os.environ', {}, clear=True):
		oauth = google_oauth_status()
		assert oauth['configured'] is False
		assert oauth['has_tokens'] is False
