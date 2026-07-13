"""SEO capability catalog — provider routing only (no SEO reasoning logic)."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoCapabilitySpec

# Evidence providers: GSC, GA4, LibreCrawl, Lighthouse, Browser Intelligence.
# Planner orchestrates collection — reasoning lives in the recommendation engine.

CAPABILITY_CATALOG: dict[str, SeoCapabilitySpec] = {
	'search_queries': SeoCapabilitySpec(
		capability_id='search_queries',
		display_name='Search queries (clicks, impressions, CTR)',
		primary_provider='search-console',
		fallback_providers=['analytics-ga4'],
		requires_api_key=False,
		requires_paid_plan=False,
		optional=False,
		fallback_available=True,
		notes='Professional mode — requires Google OAuth',
	),
	'index_status': SeoCapabilitySpec(
		capability_id='index_status',
		display_name='Index coverage and crawl issues',
		primary_provider='search-console',
		fallback_providers=['librecrawl', 'browser'],
		requires_api_key=False,
		requires_paid_plan=False,
		optional=False,
		fallback_available=True,
	),
	'traffic_metrics': SeoCapabilitySpec(
		capability_id='traffic_metrics',
		display_name='Sessions, landing pages, conversions',
		primary_provider='analytics-ga4',
		fallback_providers=['search-console'],
		requires_api_key=False,
		requires_paid_plan=False,
		optional=False,
		fallback_available=True,
		notes='Professional mode — requires Google OAuth',
	),
	'technical_crawl': SeoCapabilitySpec(
		capability_id='technical_crawl',
		display_name='Technical crawl (links, canonicals, robots, schema)',
		primary_provider='librecrawl',
		fallback_providers=['browser'],
		final_fallback='no_crawl',
		requires_api_key=False,
		requires_paid_plan=False,
		optional=False,
		fallback_available=True,
	),
	'core_web_vitals': SeoCapabilitySpec(
		capability_id='core_web_vitals',
		display_name='Core Web Vitals and lab performance',
		primary_provider='lighthouse',
		fallback_providers=['browser'],
		requires_api_key=False,
		requires_paid_plan=False,
		optional=False,
		fallback_available=True,
	),
	'rendering_verification': SeoCapabilitySpec(
		capability_id='rendering_verification',
		display_name='Client rendering and hydration evidence',
		primary_provider='browser',
		fallback_providers=[],
		final_fallback='no_render_evidence',
		requires_api_key=False,
		requires_paid_plan=False,
		optional=True,
		fallback_available=False,
	),
	'keyword_research': SeoCapabilitySpec(
		capability_id='keyword_research',
		display_name='Keyword ideas from owned search data',
		primary_provider='search-console',
		fallback_providers=[],
		final_fallback='no_data',
		requires_api_key=False,
		requires_paid_plan=False,
		optional=True,
		fallback_available=False,
		notes='Professional mode — GSC query evidence',
	),
}

# Development SEO — instant browser-scan heuristics while building (no crawl/auth).
DEVELOPMENT_AUDIT_CAPABILITIES: list[str] = [
	'rendering_verification',
]

# Professional SEO — live search data + technical evidence (async job).
PROFESSIONAL_AUDIT_CAPABILITIES: list[str] = [
	'search_queries',
	'index_status',
	'traffic_metrics',
	'technical_crawl',
	'core_web_vitals',
]

# Backward-compatible alias
DEFAULT_AUDIT_CAPABILITIES = PROFESSIONAL_AUDIT_CAPABILITIES
