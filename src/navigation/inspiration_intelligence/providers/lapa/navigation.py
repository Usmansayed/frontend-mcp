"""Lapa Ninja provider navigation knowledge."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

LAPA_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='lapa',
	display_name='Lapa Ninja',
	base_url='https://www.lapa.ninja',
	search_url_pattern='https://www.lapa.ninja/category/{query_slug}/',
	detail_url_pattern='https://www.lapa.ninja/post/{external_id}/',
	result_card_selector='a[href^="/post/"]',
	result_link_selector='a[href^="/post/"]',
	title_selector='h3 a, a[title]',
	preview_image_selector='img[src*="cdn.lapa.ninja/assets/images"]',
	pagination_kind='numbered',
	hydration_wait_ms=3000,
	headless_reliable=True,
	anti_bot_notes=[
		'HTTP archive is highly reliable — prefer /category/{name}/ over free-text ?s=',
		'CDN thumbs at cdn.lapa.ninja/assets/images/{1x|2x}/ allow image-first capture',
		'Year browse /year/YYYY/ is a stable fallback when category is unknown',
	],
	navigation_flow=[
		'Map query tokens to /category/{name}/ when possible',
		'Fallback GET /year/2026/ then homepage',
		'Parse /post/{slug}/ cards with nearby CDN thumbs',
	],
	stable_anchors=[
		'/post/',
		'/category/',
		'/year/',
		'cdn.lapa.ninja',
	],
)
