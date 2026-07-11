"""Land-book provider navigation knowledge."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

LANDBOOK_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='land-book',
	display_name='Land-book',
	base_url='https://land-book.com',
	search_url_pattern='https://land-book.com/design?search={query_slug}',
	detail_url_pattern='https://land-book.com/design/{external_id}',
	result_card_selector='a[href*="/design/"]',
	result_link_selector='a[href*="/design/"]',
	title_selector='h3, h2, img[alt]',
	preview_image_selector='img[src*="land-book"]',
	pagination_kind='load_more',
	hydration_wait_ms=8000,
	headless_reliable=False,
	anti_bot_notes=[
		'Use land-book.com without www',
		'Load-more button — click before extract',
		'Browse fallback: /design/landing-page when search empty',
		'Skip generic og-image.webp for blobs',
	],
	navigation_flow=[
		'GET /design?search={slug} or browse /design/landing-page',
		'Click load-more, scroll, run LANDBOOK_EXTRACT',
		'Filter category slugs (landing-page, design, etc.)',
	],
	stable_anchors=[
		'land-book.com/design/',
	],
)
