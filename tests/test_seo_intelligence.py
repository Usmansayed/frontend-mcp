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
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef
from navigation.seo_intelligence.registry import SeoProviderRegistry


def test_service_status_architecture_phase() -> None:
	service = SeoIntelligenceService()
	status = service.status()
	assert status['module'] == 'seo_intelligence'
	assert status['phase'] == 'architecture_v1'
	assert 'search-console' in status['providers_live_stubs']
	assert 'keyword_databases' in status['do_not_build']


def test_provider_registry_free_first() -> None:
	registry = SeoProviderRegistry()
	providers = registry.list_providers()
	ids = {p['provider_id'] for p in providers}
	assert 'search-console' in ids
	assert 'analytics-ga4' in ids
	assert 'librecrawl' in ids
	assert 'lighthouse' in ids
	assert all(p.get('free_tier') for p in providers)


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


def test_audit_returns_connections_and_degraded() -> None:
	async def _run() -> None:
		service = SeoIntelligenceService()
		result = await service.audit(SeoAuditRequest(website_url='https://example.com'))
		assert result.connections
		assert 'search-console' in result.connections
		assert result.degraded
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
