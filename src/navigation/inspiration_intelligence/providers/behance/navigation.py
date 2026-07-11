"""Behance provider navigation knowledge — preliminary Browser Intelligence notes."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

BEHANCE_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='behance',
	display_name='Behance',
	base_url='https://www.behance.net',
	search_url_pattern='https://www.behance.net/search/projects?search={query_slug}',
	detail_url_pattern='https://www.behance.net/gallery/{external_id}',
	result_card_selector='[data-project-id], .Project-cover',
	result_link_selector='a[href*="/gallery/"]',
	title_selector='[data-project-title], .Project-title',
	preview_image_selector='img[src*="behance.net"]',
	pagination_kind='infinite_scroll',
	hydration_wait_ms=6000,
	headless_reliable=True,
	anti_bot_notes=[
		'Adobe CDN assets; moderate rate limiting on rapid pagination',
		'Search is query-param based — stable for automation',
	],
	navigation_flow=[
		'URL-encode query for search param',
		'GET /search/projects?search={query}',
		'Wait for project grid hydration',
		'Extract gallery links /gallery/{id}',
	],
	stable_anchors=[
		'/gallery/{numeric_id}',
		'data-project-id attribute',
	],
)
