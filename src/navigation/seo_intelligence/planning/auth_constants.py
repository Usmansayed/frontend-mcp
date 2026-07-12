"""OAuth provider and intent constants — shared by planner modes and auth gating."""
from __future__ import annotations

GOOGLE_AUTH_PROVIDERS = frozenset({'search-console', 'analytics-ga4'})
BING_AUTH_PROVIDERS = frozenset({'bing-webmaster'})

GOOGLE_AUTH_INTENTS = frozenset(
	{
		'search_queries',
		'index_status',
		'traffic_metrics',
		'keyword_research',
		'clicks',
		'impressions',
		'ctr',
		'average_position',
		'indexed_pages',
		'crawl_issues',
		'url_inspection',
		'sitemaps',
		'coverage',
		'sessions',
		'users',
		'conversions',
		'traffic_sources',
		'landing_pages',
		'engagement',
	}
)

BING_AUTH_INTENTS = frozenset(
	{
		'bing_search_queries',
		'bing_search_performance',
		'bing_webmaster',
	}
)
