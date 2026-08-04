"""Google Search Console provider — OAuth + Search Console API."""
from __future__ import annotations

from navigation.seo_intelligence.auth.google import (
	default_date_range,
	get_valid_credentials,
	google_oauth_configured,
	gsc_inspect_url,
	gsc_list_sites,
	gsc_search_analytics,
	has_stored_tokens,
	resolve_gsc_property,
)
from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.search_console.normalize import (
	normalize_search_analytics,
	normalize_url_inspection,
)


class SearchConsoleProvider:
	provider_id = 'search-console'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		degraded: list[str] = []
		if not google_oauth_configured():
			return 'not_configured', ['google_oauth_not_configured:set_GOOGLE_OAUTH_CLIENT_ID_and_SECRET']
		if not has_stored_tokens():
			return 'pending_auth', ['google_oauth_pending:run_perception_seo_connect']
		creds = get_valid_credentials()
		if creds is None:
			return 'pending_auth', ['google_oauth_token_invalid:reconnect']
		sites, site_deg = await gsc_list_sites(creds)
		degraded.extend(site_deg)
		if sites:
			return 'connected', degraded
		return 'degraded', degraded + ['gsc_no_sites_or_api_error']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		creds = get_valid_credentials()
		if creds is None:
			return [], ['search_console_not_authenticated']

		site_url = resolve_gsc_property(request.property_url, request.website_url)
		if not site_url:
			return [], ['search_console_property_missing:set_property_url_or_website_url']

		evidence: list[SeoEvidenceRef] = []
		degraded: list[str] = []
		start_date, end_date = default_date_range()

		query_payload, query_deg = await gsc_search_analytics(
			creds,
			site_url=site_url,
			start_date=start_date,
			end_date=end_date,
			dimensions=['query'],
			row_limit=50,
		)
		degraded.extend(query_deg)
		if query_payload:
			evidence.extend(
				normalize_search_analytics(
					query_payload,
					site_url=site_url,
					dimensions=['query'],
				)
			)

		inspect_urls = _inspection_urls(request)
		for index, page_url in enumerate(inspect_urls):
			payload, inspect_deg = await gsc_inspect_url(
				creds,
				site_url=site_url,
				inspection_url=page_url,
			)
			degraded.extend(inspect_deg)
			if payload:
				evidence.extend(
					normalize_url_inspection(
						payload,
						site_url=site_url,
						inspection_url=page_url,
						index=index,
					)
				)

		if not evidence:
			degraded.append('search_console_no_evidence')
		return evidence, degraded


def _inspection_urls(request: SeoAuditRequest) -> list[str]:
	urls: list[str] = []
	if request.website_url.strip():
		urls.append(request.website_url.strip())
	prop = request.property_url.strip()
	if prop.startswith('http') and prop not in urls:
		urls.append(prop)
	return urls[:10]
