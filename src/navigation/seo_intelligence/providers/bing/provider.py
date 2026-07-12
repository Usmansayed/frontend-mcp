"""Bing Webmaster Tools provider — optional OAuth or API key."""
from __future__ import annotations

from navigation.seo_intelligence.auth.bing import (
	bing_oauth_configured,
	bwm_get_query_stats,
	bwm_get_user_sites,
	get_valid_access_token,
	has_stored_tokens,
	resolve_bing_site_url,
)
from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.bing.normalize import normalize_query_stats


class BingWebmasterProvider:
	provider_id = 'bing-webmaster'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		degraded: list[str] = []
		if not has_stored_tokens():
			return 'not_configured', ['bing_optional:connect_bing_oauth_or_api_key']
		token, _mode = get_valid_access_token()
		if not token:
			return 'pending_auth', ['bing_token_invalid:reconnect']
		sites, site_deg = await bwm_get_user_sites()
		degraded.extend(site_deg)
		site_url = resolve_bing_site_url(request.bing_site_url, request.website_url)
		if sites and site_url:
			return 'connected', degraded
		if sites:
			return 'degraded', degraded + ['bing_site_url_missing:auto_discovery_pending']
		return 'degraded', degraded + ['bing_no_sites_or_api_error']

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		if not has_stored_tokens():
			return [], ['bing_skipped:not_connected']

		site_url = resolve_bing_site_url(request.bing_site_url, request.website_url)
		if not site_url:
			return [], ['bing_site_url_missing']

		payload, degraded = await bwm_get_query_stats(site_url)
		if payload is None:
			return [], degraded
		evidence, norm_deg = normalize_query_stats(payload, site_url=site_url)
		return evidence, degraded + norm_deg
