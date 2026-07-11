"""Awwwards provider navigation knowledge — preliminary Browser Intelligence notes."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

AWWWARDS_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='awwwards',
	display_name='Awwwards',
	base_url='https://www.awwwards.com',
	search_url_pattern='https://www.awwwards.com/websites/?search={query_slug}',
	detail_url_pattern='https://www.awwwards.com/sites/{external_id}',
	result_card_selector='.js-item-url, .card-web',
	result_link_selector='a[href*="/sites/"]',
	title_selector='.title, h3',
	preview_image_selector='img[src*="awwwards.com"]',
	pagination_kind='numbered',
	hydration_wait_ms=5000,
	headless_reliable=True,
	anti_bot_notes=[
		'Cookie consent banner may block first interaction',
		'Category filters on /websites/ — prefer search param when available',
	],
	navigation_flow=[
		'GET /websites/?search={slug}',
		'Dismiss cookie banner if present',
		'Parse site cards linking to /sites/{slug-id}',
	],
	stable_anchors=[
		'/sites/',
		'awwwards.com/websites',
	],
)
