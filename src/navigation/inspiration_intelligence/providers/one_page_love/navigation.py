"""One Page Love provider navigation knowledge."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

ONEPAGELOVE_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='onepagelove',
	display_name='One Page Love',
	base_url='https://onepagelove.com',
	search_url_pattern='https://onepagelove.com/genre/{query_slug}',
	detail_url_pattern='https://onepagelove.com/{external_id}',
	result_card_selector='a[href^="https://onepagelove.com/"]',
	result_link_selector='a[href^="https://onepagelove.com/"]',
	title_selector='h2, .card-title',
	preview_image_selector='img[src*="assets.onepagelove.com"]',
	pagination_kind='numbered',
	hydration_wait_ms=4000,
	headless_reliable=True,
	anti_bot_notes=[
		'Free-text ?s= search often returns zero — prefer /genre/ and /inspiration archive',
		'HTTP archive is reliable; optional ONEPAGELOVE_API_KEY for structured API',
		'Filter nav links — require assets.onepagelove.com screenshot near card',
	],
	navigation_flow=[
		'Map query tokens to /genre/{name} when possible',
		'Fallback GET /inspiration (always populated)',
		'Parse slug links with screenshot assets',
	],
	stable_anchors=[
		'/inspiration',
		'/genre/',
		'assets.onepagelove.com',
	],
)
