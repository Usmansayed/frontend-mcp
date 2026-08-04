"""SEO Intelligence tests — architecture phase."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.seo_intelligence import SeoAuditRequest, SeoIntelligenceService
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditMode, SeoAuditResult, SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.registry import SeoProviderRegistry


def test_service_status_production_phase() -> None:
	service = SeoIntelligenceService()
	status = service.status()
	assert status['module'] == 'seo_intelligence'
	assert status['phase'] == 'agent_ready_v4'
	assert status['philosophy'] == 'evidence_first_seo_intelligence'
	assert status['default_mode'] == 'development'
	assert 'development' in status['modes']
	assert 'professional' in status['modes']
	assert 'search-console' in status['providers_live']
	assert 'keyword_databases' in status['do_not_build']
	assert 'integrations' in status


def test_provider_registry_evidence_sources() -> None:
	registry = SeoProviderRegistry()
	providers = registry.list_providers()
	ids = {p['provider_id'] for p in providers}
	assert 'search-console' in ids
	assert 'librecrawl' in ids
	assert 'browser' in ids
	assert 'openseo' not in ids
	free_core = [p for p in providers if p['provider_id'] in ('search-console', 'analytics-ga4', 'librecrawl', 'lighthouse')]
	assert all(p.get('free_tier') for p in free_core)


def test_planner_routes_keyword_research_to_gsc() -> None:
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(
		website_url='https://example.com',
		intents=['keyword_research'],
		mode=SeoAuditMode.PROFESSIONAL,
	)
	route = planner.route_capability('keyword_research', request, {'search-console': 'connected'})
	assert route is not None
	assert route.chosen_provider == 'search-console'


def test_planner_routes_technical_crawl_to_librecrawl() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(
		website_url='https://example.com',
		mode=SeoAuditMode.PROFESSIONAL,
		intents=['technical_crawl'],
	)
	with patch.dict('os.environ', {'LIBRECRAWL_BASE_URL': 'http://localhost:8080'}):
		route = planner.route_capability(
			'technical_crawl',
			request,
			{'librecrawl': 'connected'},
		)
	assert route is not None
	assert route.chosen_provider == 'librecrawl'


def test_planner_adds_rendering_when_scan_id_present() -> None:
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', scan_id='scan-1')
	caps = planner.resolve_capabilities(request)
	assert 'rendering_verification' in caps


def test_planner_falls_back_to_librecrawl_for_index_when_gsc_unavailable() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', intents=['index_status'])
	with patch.dict('os.environ', {'LIBRECRAWL_BASE_URL': 'http://localhost:8080'}):
		route = planner.route_capability(
			'index_status',
			request,
			{'search-console': 'not_configured', 'librecrawl': 'connected'},
		)
	assert route is not None
	assert route.chosen_provider == 'librecrawl'


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
			page_url='https://example.com/pricing',
			severity='high',
		),
		SeoEvidenceRef(
			evidence_id='b1',
			provider_id='browser',
			kind=SeoEvidenceKind.RENDERING_ISSUE,
			title='Hydration error',
			summary='Client render failed',
			page_url='https://example.com/pricing',
			severity='high',
		),
	]
	findings = run_cross_analysis(evidence, base_url='https://example.com')
	assert findings
	assert all(f.get('evidence_ids') for f in findings)


def test_implicit_professional_from_search_intent() -> None:
	from navigation.seo_intelligence.planning.modes import resolve_effective_mode
	from navigation.seo_intelligence.setup.auth_requirements import audit_blocked_by_auth

	request = SeoAuditRequest(website_url='https://example.com', intents=['search_queries'])
	assert resolve_effective_mode(request).value == 'professional'
	with patch('navigation.seo_intelligence.setup.auth_requirements.has_google_tokens', return_value=False):
		assert audit_blocked_by_auth(request) is True


def test_development_probe_skips_non_browser_providers() -> None:
	from navigation.core.scan_registry import ScanRegistry
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator

	scans = ScanRegistry()
	record = scans.register(
		session_id='s1',
		run_id='r1',
		url='http://localhost:5173/',
		observation={'url': 'http://localhost:5173/', 'dev_insights': {'issues': []}},
	)
	request = SeoAuditRequest(
		website_url='http://localhost:5173/',
		scan_id=record.scan_id,
		mode=SeoAuditMode.DEVELOPMENT,
	)

	async def _run() -> None:
		orch = SeoAuditOrchestrator(scan_registry=scans)
		connections = await orch._probe_connections(request)
		assert connections['browser'] == 'connected'
		assert connections.get('librecrawl') == 'not_configured'
		assert connections.get('search-console') == 'not_configured'

	asyncio.run(_run())


def test_development_audit_fast_with_scan() -> None:
	from navigation.core.scan_registry import ScanRegistry
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator

	scans = ScanRegistry()
	record = scans.register(
		session_id='s1',
		run_id='r1',
		url='http://localhost:5173/forms/validation',
		observation={
			'url': 'http://localhost:5173/forms/validation',
			'dev_insights': {
				'issues': [{'kind': 'meta', 'message': 'Missing meta description', 'tier': 'advisory'}],
			},
		},
	)
	request = SeoAuditRequest(
		website_url='http://localhost:5173/forms/validation',
		scan_id=record.scan_id,
		repo_root=str(Path(__file__).resolve().parents[1] / 'sandbox'),
		mode=SeoAuditMode.DEVELOPMENT,
	)

	async def _run() -> None:
		orch = SeoAuditOrchestrator(scan_registry=scans)
		result = await orch.development_audit(request)
		assert result.evidence
		assert result.recommendations
		assert result.mode == 'development'

	asyncio.run(_run())


def test_planner_development_mode_excludes_google() -> None:
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', mode=SeoAuditMode.DEVELOPMENT)
	routes, providers = planner.build_plan(
		request,
		{'search-console': 'connected', 'analytics-ga4': 'connected', 'lighthouse': 'connected'},
	)
	assert 'search-console' not in providers
	assert 'analytics-ga4' not in providers
	cap_ids = {r.capability_id for r in routes}
	assert 'search_queries' not in cap_ids
	assert 'technical_crawl' not in cap_ids
	assert 'rendering_verification' in cap_ids


def test_planner_professional_mode_includes_gsc() -> None:
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.planning.planner import SeoAuditPlanner

	planner = SeoAuditPlanner()
	request = SeoAuditRequest(website_url='https://example.com', mode=SeoAuditMode.PROFESSIONAL)
	caps = planner.resolve_capabilities(request)
	assert 'search_queries' in caps
	assert 'traffic_metrics' in caps


def test_development_practices_from_technical_evidence() -> None:
	from navigation.seo_intelligence.analysis.development_practices import detect_development_practices

	evidence = [
		SeoEvidenceRef(
			evidence_id='t1',
			provider_id='librecrawl',
			kind=SeoEvidenceKind.TECHNICAL_ISSUE,
			title='Missing meta description',
			summary='No meta description on homepage',
			severity='medium',
		),
	]
	findings = detect_development_practices(evidence)
	assert any(f['analysis_id'] == 'dev_practice_metadata' for f in findings)


def test_recommendation_pipeline_includes_reasoning_context() -> None:
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline

	evidence = [
		SeoEvidenceRef(
			evidence_id='q1',
			provider_id='search-console',
			kind=SeoEvidenceKind.SEARCH_QUERY,
			title='example query',
			summary='low ctr',
			metadata={'impressions': 200, 'ctr': 0.01, 'position': 12},
		),
	]
	recs, correlations, context = run_recommendation_pipeline(
		evidence,
		audit_id='audit_test_pipeline',
		mode=SeoAuditMode.PROFESSIONAL,
		website_url='https://example.com',
		providers={'search-console': 'connected'},
	)
	assert context['schema_version'] == '2.0'
	assert context['meta']['mode'] == 'professional'
	assert context['evidence_count'] == 1
	assert context['pages']
	assert correlations
	assert any(r.root_cause for r in recs)


def test_opportunity_detection_high_impressions_low_ctr() -> None:
	from navigation.seo_intelligence.analysis.opportunities import detect_opportunities

	evidence = [
		SeoEvidenceRef(
			evidence_id='q1',
			provider_id='search-console',
			kind=SeoEvidenceKind.SEARCH_QUERY,
			title='brand term',
			summary='',
			metadata={'impressions': 500, 'ctr': 0.005, 'position': 4},
		),
	]
	opps = detect_opportunities(evidence)
	assert any(o.get('analysis_id', '').startswith('opportunity_low_ctr') for o in opps)


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
			page_url='https://example.com/missing',
			severity='high',
		),
		SeoEvidenceRef(
			evidence_id='i1',
			provider_id='search-console',
			kind=SeoEvidenceKind.INDEX_STATUS,
			title='Not indexed',
			summary='Excluded',
			page_url='https://example.com/missing',
			severity='high',
		),
	]
	findings = run_cross_analysis(evidence, base_url='https://example.com')
	assert any(f['analysis_id'] == 'technical_index_correlation' for f in findings)


def test_verification_passes_when_technical_issue_resolved() -> None:
	from navigation.seo_intelligence.models import SeoRecommendation
	from navigation.seo_intelligence.verification.loop import evaluate_verification

	eid = 'ev:librecrawl:technical_issue:test404'
	baseline = SeoAuditResult(
		request=SeoAuditRequest(website_url='https://example.com'),
		evidence=[
			SeoEvidenceRef(
				evidence_id=eid,
				provider_id='librecrawl',
				kind=SeoEvidenceKind.TECHNICAL_ISSUE,
				title='HTTP 404',
				summary='not found',
				metric_value=404.0,
				metric_unit='status_code',
				severity='high',
			),
		],
		recommendations=[
			SeoRecommendation(
				recommendation_id='rec_404',
				title='Fix 404',
				summary='not found',
				priority='high',
				category='technical_issue',
				evidence_ids=[eid],
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
		recommendation_ids=['rec_404'],
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
	assert evidence[0].evidence_id.startswith('ev:search-console:')


def test_seo_connect_status() -> None:
	from unittest.mock import patch

	from navigation.seo_intelligence.auth.google import google_oauth_status

	with (
		patch.dict('os.environ', {}, clear=True),
		patch('navigation.seo_intelligence.auth.google.has_stored_tokens', return_value=False),
	):
		oauth = google_oauth_status()
		assert oauth['configured'] is False
		assert oauth['has_tokens'] is False


def test_load_project_env_from_example_template() -> None:
	from navigation.core.env import find_project_root, load_project_env

	root = find_project_root()
	assert root is not None
	example = root / '.env.example'
	assert example.is_file()
	# Do not require .env — only verify loader runs without error when file missing
	path = load_project_env()
	# path is None when .env absent, or Path when present
	assert path is None or path.is_file()
