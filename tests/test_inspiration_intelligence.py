"""Inspiration Intelligence tests — priority discovery and provider adapters."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.inspiration_intelligence import InspirationIntelligenceService
from navigation.inspiration_intelligence.community_intelligence.planner import build_community_plan
from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail, extract_og_image
from navigation.inspiration_intelligence.browser.policy import detect_block_signal
from navigation.inspiration_intelligence.discovery.inspiration import has_enough_high_confidence
from navigation.inspiration_intelligence.intent.parser import parse_intent
from navigation.inspiration_intelligence.models import (
	InspirationCandidate,
	InspirationDiscoveryRequest,
	InspirationRankedCandidate,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.planning.search_planner import DEFAULT_PROVIDER_PRIORITY
from navigation.inspiration_intelligence.providers.dribbble.parser import parse_search_html, query_to_slug
from navigation.inspiration_intelligence.providers.dribbble.provider import DribbbleProvider
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.selection.planner import build_selection_plan

_SAMPLE_HTML = """
<li class="shot-thumbnail">
  <a href="/shots/12345-saas-dashboard" aria-label="View SaaS Dashboard UI">
    <img src="https://cdn.dribbble.com/userupload/1.png" />
  </a>
</li>
<li class="shot-thumbnail">
  <a href="/shots/67890-saas-dashboard-alt" aria-label="View SaaS Dashboard Kit">
    <img src="https://cdn.dribbble.com/userupload/2.png" />
  </a>
</li>
<li class="shot-thumbnail">
  <a href="/shots/11111-minimal-saas" aria-label="View Minimal SaaS Landing">
    <img src="https://cdn.dribbble.com/userupload/3.png" />
  </a>
</li>
"""


def test_query_slug_normalization() -> None:
	assert query_to_slug('SaaS Landing Page!') == 'saas-landing-page'


def test_dribbble_parser_extracts_shots() -> None:
	hits = parse_search_html(_SAMPLE_HTML)
	assert len(hits) == 3
	assert hits[0].shot_id == '12345'
	assert 'SaaS Dashboard' in hits[0].title
	assert 'cdn.dribbble.com' in hits[0].preview_url


def test_dribbble_provider_discovers_from_html() -> None:
	async def _fake_fetch(url: str) -> str:
		_ = url
		return _SAMPLE_HTML

	provider = DribbbleProvider(fetch_html=_fake_fetch)
	intent = parse_intent('saas dashboard')
	plan = InspirationSearchPlan(seed_query=intent.raw_query)
	community_plan = build_community_plan(intent, plan)
	candidates, degraded = asyncio.run(
		provider.discover_candidates(plan, community_plan=community_plan, intent=intent, max_results=5)
	)
	assert len(candidates) == 3
	assert candidates[0].provider_id == 'dribbble'
	assert candidates[0].external_id == '12345'
	assert not any('fetch_failed' in d for d in degraded)
	assert any('dribbble_auth_hint' in d for d in degraded)
	assert candidates[0].metadata.get('fetch_tier') == 'http'


def test_og_image_extraction() -> None:
	html = '<meta property="og:image" content="https://cdn.dribbble.com/shot.png" />'
	assert extract_og_image(html) == 'https://cdn.dribbble.com/shot.png'


def test_block_detection() -> None:
	assert detect_block_signal('<html>403 ERROR</html>') == 'bot_challenge_detected'
	assert detect_block_signal('normal page', status_code=429) == 'http_429'


def test_og_enrich_from_detail_html() -> None:
	import navigation.inspiration_intelligence.browser.fetch as fetch_mod

	def _fake_get(url: str, *, headers: object = None, timeout: float = 30.0) -> tuple[str, int | None, str | None]:
		_ = url, headers, timeout
		return (
			'<meta property="og:image" content="https://cdn.dribbble.com/full.png" />'
			'<meta property="og:title" content="SaaS UI" />',
			200,
			None,
		)

	orig = fetch_mod.http_get
	fetch_mod.http_get = _fake_get  # type: ignore[assignment]
	try:
		preview, title, degraded = enrich_preview_from_detail('https://dribbble.com/shots/1')
		assert preview == 'https://cdn.dribbble.com/full.png'
		assert title == 'SaaS UI'
		assert not degraded
	finally:
		fetch_mod.http_get = orig


def test_provider_priority_order() -> None:
	assert DEFAULT_PROVIDER_PRIORITY[0] == 'dribbble'
	assert DEFAULT_PROVIDER_PRIORITY[2] == 'onepagelove'
	assert DEFAULT_PROVIDER_PRIORITY[-1] == 'land-book'


def test_onepagelove_parser_filters_nav_links() -> None:
	from navigation.inspiration_intelligence.providers.gallery_parse import parse_onepagelove_html

	html = """
	<a href="https://onepagelove.com/about">About</a>
	<a href="https://onepagelove.com/landmark">
	  <img src="https://assets.onepagelove.com/cdn-cgi/image/width=420/wp-content/uploads/shot.jpg" />
	</a>
	"""
	hits = parse_onepagelove_html(html, 'https://onepagelove.com/inspiration')
	assert 'about' not in {h['external_id'] for h in hits}
	assert any(h['external_id'] == 'landmark' for h in hits)


def test_normalize_image_url_preserves_cdn_commas() -> None:
	from navigation.inspiration_intelligence.tools.media_urls import normalize_image_url

	url = 'https://assets.onepagelove.com/cdn-cgi/image/width=840,height=560/file.jpg'
	assert normalize_image_url(url) == url


def test_to_medium_inspiration_url_onepagelove() -> None:
	from navigation.inspiration_intelligence.tools.media_urls import to_medium_inspiration_url

	url = 'https://assets.onepagelove.com/cdn-cgi/image/width=840,quality=85/file.jpg'
	out = to_medium_inspiration_url(url, provider_id='onepagelove')
	assert 'width=480' in out
	assert 'quality=75' in out


def test_blob_store_session_lifecycle(tmp_path: Path, monkeypatch) -> None:
	from PIL import Image

	from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

	blob_root = tmp_path / 'blobs'
	sessions_file = tmp_path / 'sessions.json'
	monkeypatch.setenv('INSPIRATION_BLOB_ROOT', str(blob_root))
	monkeypatch.setenv('INSPIRATION_SESSIONS_CACHE', str(sessions_file))
	monkeypatch.setenv('INSPIRATION_BLOB_TTL_HOURS', '24')

	img = Image.new('RGB', (1200, 800), color=(30, 120, 200))
	png_path = tmp_path / 'shot.png'
	img.save(png_path, format='PNG')

	store = InspirationBlobStore()
	session_id = store.create_session(purpose='test')
	blob = store.materialize(
		session_id,
		preview_url=str(png_path),
		page_url='https://example.com',
		provider_id='dribbble',
		candidate_id='c1',
		title='Test Shot',
	)
	assert blob
	assert Path(blob).is_file()
	assert Path(blob).suffix == '.jpg'
	assert Path(blob).stat().st_size > 0

	with Image.open(blob) as saved:
		assert saved.size[0] <= 960

	removed = store.end_session(session_id)
	assert removed == 1
	assert not (blob_root / session_id).exists()


def test_land_book_og_skips_blob(tmp_path: Path, monkeypatch) -> None:
	from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

	blob_root = tmp_path / 'blobs'
	monkeypatch.setenv('INSPIRATION_BLOB_ROOT', str(blob_root))
	monkeypatch.setenv('INSPIRATION_SESSIONS_CACHE', str(tmp_path / 'sessions.json'))

	store = InspirationBlobStore()
	session_id = store.create_session()
	blob = store.materialize(
		session_id,
		preview_url='https://land-book.com/og-image.webp',
		page_url='https://land-book.com/design/foo',
		provider_id='land-book',
		candidate_id='x',
		title='Foo',
	)
	assert blob is None


def test_inspiration_guide_mcp_resource() -> None:
	from navigation.mcp.resources import read_resource

	mime, payload, is_blob = read_resource('perception://inspiration-guide')
	assert mime == 'text/markdown'
	assert 'Dribbble' in payload
	assert 'recent.design' in payload
	assert not is_blob


def test_production_min_blocks_premature_early_stop() -> None:
	low = [
		InspirationCandidate(
			candidate_id='x',
			title='X',
			source='behance',
			provider_id='behance',
			discovery_score=0.8,
		),
	]
	# One high-confidence hit is not enough in fast mode (needs 2)
	assert not has_enough_high_confidence(low, max_results=12)


def test_early_stop_logic() -> None:
	high = [
		InspirationCandidate(
			candidate_id='a',
			title='A',
			source='dribbble',
			provider_id='dribbble',
			discovery_score=0.8,
		),
		InspirationCandidate(
			candidate_id='b',
			title='B',
			source='dribbble',
			provider_id='dribbble',
			discovery_score=0.7,
		),
		InspirationCandidate(
			candidate_id='c',
			title='C',
			source='dribbble',
			provider_id='dribbble',
			discovery_score=0.6,
		),
	]
	assert has_enough_high_confidence(high, max_results=12)
	low = [
		InspirationCandidate(
			candidate_id='x',
			title='X',
			source='dribbble',
			provider_id='dribbble',
			discovery_score=0.3,
		),
	]
	assert not has_enough_high_confidence(low, max_results=12)


def test_discover_with_mock_dribbble_stops_early() -> None:
	async def _fake_fetch(url: str) -> str:
		_ = url
		return _SAMPLE_HTML

	registry = InspirationProviderRegistry()
	registry._providers['dribbble'] = DribbbleProvider(fetch_html=_fake_fetch)

	result = asyncio.run(
		InspirationIntelligenceService(providers=registry).discover(
			InspirationDiscoveryRequest(query='saas dashboard inspiration', max_candidates=5)
		)
	)
	assert result.candidates
	assert any('discovery_early_stop:dribbble' in d for d in result.degraded)
	assert result.search_plan.provider_ids[0] == 'dribbble'


def test_selection_planner_dedupes_similar_titles() -> None:
	ranked = [
		InspirationRankedCandidate(
			candidate=InspirationCandidate(
				candidate_id='a',
				title='Analytics Dashboard UI',
				source='dribbble',
				provider_id='dribbble',
				metadata={'design_system': 'analytics dashboard'},
				discovery_score=0.95,
			),
			overall_score=0.95,
		),
		InspirationRankedCandidate(
			candidate=InspirationCandidate(
				candidate_id='b',
				title='Analytics Dashboard Pro',
				source='dribbble',
				provider_id='dribbble',
				metadata={'design_system': 'analytics dashboard'},
				discovery_score=0.93,
			),
			overall_score=0.93,
		),
	]
	plan = build_selection_plan(ranked)
	assert len({s.design_system_key for s in plan.selected}) == len(plan.selected)
