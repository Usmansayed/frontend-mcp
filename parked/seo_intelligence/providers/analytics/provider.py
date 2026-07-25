"""Google Analytics 4 provider — OAuth + Data API."""
from __future__ import annotations

from navigation.seo_intelligence.auth.google import (
	default_date_range,
	ga4_run_report,
	get_valid_credentials,
	google_oauth_configured,
	has_stored_tokens,
	resolve_ga4_property_id,
)
from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.analytics.normalize import normalize_ga4_report


class Ga4Provider:
	provider_id = 'analytics-ga4'

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		if not google_oauth_configured():
			return 'not_configured', ['google_oauth_not_configured:set_GOOGLE_OAUTH_CLIENT_ID_and_SECRET']
		if not has_stored_tokens():
			return 'pending_auth', ['google_oauth_pending:run_perception_seo_connect']
		property_id = resolve_ga4_property_id(request.ga4_property_id, request.website_url)
		if not property_id:
			return 'not_configured', ['ga4_property_missing:connect_google_for_auto_discovery']
		creds = get_valid_credentials()
		if creds is None:
			return 'pending_auth', ['google_oauth_token_invalid:reconnect']
		return 'connected', []

	async def collect(self, request: SeoAuditRequest) -> tuple[list[SeoEvidenceRef], list[str]]:
		creds = get_valid_credentials()
		if creds is None:
			return [], ['ga4_not_authenticated']

		property_id = resolve_ga4_property_id(request.ga4_property_id, request.website_url)
		if not property_id:
			return [], ['ga4_property_missing']

		start_date, end_date = default_date_range()
		payload, degraded = await ga4_run_report(
			creds,
			property_id=property_id,
			start_date=start_date,
			end_date=end_date,
		)
		if payload is None:
			return [], degraded or ['ga4_report_failed']
		evidence = normalize_ga4_report(payload, property_id=property_id, base_url=request.website_url)
		if not evidence:
			degraded.append('ga4_no_rows')
		return evidence, degraded
