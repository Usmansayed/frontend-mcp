"""Godly provider navigation knowledge — recent.design redirect."""
from __future__ import annotations

from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge

GODLY_NAVIGATION = ProviderNavigationKnowledge(
	provider_id='godly',
	display_name='Godly',
	base_url='https://recent.design',
	search_url_pattern='https://godly.website/?search={query_slug}',
	detail_url_pattern='https://recent.design/i/{external_id}',
	result_card_selector='a[href*="/i/"]',
	result_link_selector='a[href*="/i/"]',
	title_selector='h2, h3, img[alt]',
	preview_image_selector='img[src*="recent.design"], img[src*="godly"]',
	pagination_kind='infinite_scroll',
	hydration_wait_ms=7000,
	headless_reliable=False,
	anti_bot_notes=[
		'godly.website redirects to recent.design',
		'Card links use /i/{id}-{slug} — not /website/',
		'Next.js — wait for hydration before extract',
	],
	navigation_flow=[
		'Load godly.website or recent.design',
		'Wait for grid mount (~7s)',
		'Run GODLY_EXTRACT for /i/ links',
	],
	stable_anchors=[
		'recent.design/i/',
		'godly.website',
	],
)
