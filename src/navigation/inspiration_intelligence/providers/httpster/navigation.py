"""Httpster provider navigation knowledge."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

HTTPSTER_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='httpster',
	display_name='Httpster',
	base_url='https://httpster.net',
	search_url_pattern='https://httpster.net/type/{query_slug}/',
	detail_url_pattern='https://httpster.net/website/{external_id}/',
	result_card_selector='article.Preview',
	result_link_selector='a.Preview__title[href^="/website/"]',
	title_selector='a.Preview__title',
	preview_image_selector='img.Preview__img',
	pagination_kind='none',
	hydration_wait_ms=2000,
	headless_reliable=True,
	anti_bot_notes=[
		'Homepage + /type/ + /style/ grids are static HTML with local /assets/media thumbs',
		'/websites.json lists titles/urls only — no image URLs; prefer HTML Preview cards',
		'No free-text search; map query tokens to type/style paths',
	],
	navigation_flow=[
		'Map query to /type/ or /style/ when possible',
		'Fallback GET homepage grid',
		'Parse article.Preview blocks (img + title href)',
	],
	stable_anchors=[
		'/website/',
		'/type/',
		'/style/',
		'/assets/media/',
	],
)
