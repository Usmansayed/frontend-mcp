"""SiteInspire provider navigation knowledge — preliminary Browser Intelligence notes."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

SITEINSPIRE_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='siteinspire',
	display_name='SiteInspire',
	base_url='https://www.siteinspire.com',
	search_url_pattern='https://www.siteinspire.com/search?q={query_slug}',
	detail_url_pattern='https://www.siteinspire.com/website/{external_id}',
	result_card_selector='.website-item, article.website',
	result_link_selector='a[href*="/website/"]',
	title_selector='h2, .website-title',
	preview_image_selector='img.website-screenshot',
	pagination_kind='numbered',
	hydration_wait_ms=4000,
	headless_reliable=True,
	anti_bot_notes=[
		'Tag/category browse often more stable than free-text search',
		'Thumbnail-heavy grid — lazy-loaded images',
	],
	navigation_flow=[
		'Prefer /search?q= or category tag URLs',
		'Wait for lazy image placeholders to resolve',
		'Extract /website/{id} detail links',
	],
	stable_anchors=[
		'/website/{id}',
		'siteinspire.com/websites',
	],
)
