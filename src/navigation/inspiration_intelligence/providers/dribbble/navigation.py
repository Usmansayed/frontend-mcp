"""Dribbble provider navigation knowledge — from Browser Intelligence sessions."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

DRIBBBLE_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='dribbble',
	display_name='Dribbble',
	base_url='https://dribbble.com',
	search_url_pattern='https://dribbble.com/search/{query_slug}',
	detail_url_pattern='https://dribbble.com/shots/{external_id}',
	result_card_selector='li.shot-thumbnail, [data-thumbnail-id]',
	result_link_selector='a[href*="/shots/"]',
	title_selector='a[aria-label^="View"]',
	preview_image_selector='img[src*="cdn.dribbble.com"]',
	pagination_kind='infinite_scroll',
	hydration_wait_ms=9000,
	headless_reliable=False,
	anti_bot_notes=[
		'AWS WAF challenge on first load — wait 8–10s before DOM queries',
		'Headless may render blank until hydration completes',
		'Direct search URL preferred over form submit',
	],
	navigation_flow=[
		'Build slug: lowercase query, spaces → hyphens',
		'GET /search/{slug}',
		'Wait hydration_wait_ms',
		'Collect shot links matching /shots/{id}',
		'Optional: open detail page for full-size preview capture',
	],
	stable_anchors=[
		'/shots/{numeric_id}',
		'cdn.dribbble.com/userupload',
		'aria-label="View …"',
	],
)
