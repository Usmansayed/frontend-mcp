"""SEO onboarding — website URL only; Google/Bing OAuth on demand."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from navigation.seo_intelligence.auth import bing as bing_api
from navigation.seo_intelligence.auth import google as google_api
from navigation.seo_intelligence.auth.google import (
	build_authorization_url as build_google_authorization_url,
	exchange_authorization_code as exchange_google_authorization_code,
	get_valid_credentials,
	google_oauth_configured,
	gsc_list_sites,
	has_stored_tokens as has_google_tokens,
)
from navigation.seo_intelligence.models import SeoAuditRequest
from navigation.seo_intelligence.setup.discovery import (
	normalize_website_url,
	pick_bing_site,
	pick_ga4_property,
	pick_gsc_property,
)
from navigation.seo_intelligence.setup.site_store import SeoSiteProfile, SeoSiteStore


class SeoOnboardingService:
	def __init__(self, *, site_store: SeoSiteStore | None = None) -> None:
		self._sites = site_store or SeoSiteStore()

	async def register_website(self, website_url: str) -> dict[str, Any]:
		"""Initial setup — website URL only. No OAuth."""
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		profile = self._sites.ensure(normalized)
		self._sites.save(profile)
		return {
			'website_url': normalized,
			'ready': True,
			'step': 'registered',
			'profile': profile.to_dict(),
			'onboarding_steps': ['website_url'],
		}

	async def site_status(self, website_url: str) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			return {'ready': False, 'error': 'website_url_required'}
		profile = self._sites.get(normalized) or self._sites.ensure(normalized)
		return {
			'website_url': normalized,
			'ready': True,
			'website_registered': True,
			'google_connected': profile.google_connected and has_google_tokens(),
			'bing_connected': profile.bing_connected and bing_api.has_stored_tokens(),
			'auto_configured': profile.auto_configured,
			'profile': profile.to_dict(),
			'onboarding_steps': ['website_url'],
			'auth_on_demand': True,
		}

	async def start_google_connect(self, website_url: str) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		if not google_oauth_configured():
			raise RuntimeError('google_oauth_not_configured_by_operator')
		self._sites.ensure(normalized)
		return {
			'website_url': normalized,
			'provider': 'google',
			'authorization_url': build_google_authorization_url(),
			'step': 'authorize_google',
		}

	async def complete_google_connect(
		self,
		website_url: str,
		code: str,
		*,
		redirect_uri: str | None = None,
	) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		exchange_google_authorization_code(code.strip(), redirect_uri=redirect_uri)
		profile, notes = await self._auto_discover_google(normalized)
		profile.google_connected = True
		profile.auto_configured = bool(profile.gsc_property_url or profile.ga4_property_id)
		profile.discovery_notes = notes
		self._sites.save(profile)
		return {
			'website_url': normalized,
			'provider': 'google',
			'step': 'ready' if profile.auto_configured else 'partial',
			'profile': profile.to_dict(),
			'discovery_notes': notes,
		}

	async def start_bing_connect(self, website_url: str) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		self._sites.ensure(normalized)
		if not bing_api.bing_oauth_configured():
			raise RuntimeError('bing_oauth_not_configured_use_api_key_or_operator_oauth')
		return {
			'website_url': normalized,
			'provider': 'bing',
			'authorization_url': bing_api.build_authorization_url(),
			'step': 'authorize_bing',
			'api_key_supported': True,
		}

	async def complete_bing_connect(
		self,
		website_url: str,
		code: str,
		*,
		redirect_uri: str | None = None,
	) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		bing_api.exchange_authorization_code(code.strip(), redirect_uri_override=redirect_uri)
		profile, notes = await self._auto_discover_bing(normalized)
		profile.bing_connected = bool(profile.bing_site_url)
		profile.discovery_notes = list(profile.discovery_notes) + notes
		self._sites.save(profile)
		return {
			'website_url': normalized,
			'provider': 'bing',
			'step': 'ready' if profile.bing_connected else 'partial',
			'profile': profile.to_dict(),
			'discovery_notes': notes,
		}

	async def complete_bing_api_key(self, website_url: str, api_key: str) -> dict[str, Any]:
		normalized = normalize_website_url(website_url)
		if not normalized:
			raise ValueError('website_url_required')
		bing_api.store_api_key(api_key.strip())
		profile, notes = await self._auto_discover_bing(normalized)
		profile.bing_connected = bool(profile.bing_site_url)
		profile.discovery_notes = list(profile.discovery_notes) + notes
		self._sites.save(profile)
		return {
			'website_url': normalized,
			'provider': 'bing',
			'auth_mode': 'api_key',
			'step': 'ready' if profile.bing_connected else 'partial',
			'profile': profile.to_dict(),
			'discovery_notes': notes,
		}

	async def refresh_discovery(self, website_url: str, *, provider: str = 'all') -> SeoSiteProfile:
		normalized = normalize_website_url(website_url)
		profile = self._sites.ensure(normalized)
		all_notes: list[str] = list(profile.discovery_notes)

		if provider in {'all', 'google'} and has_google_tokens():
			profile, notes = await self._auto_discover_google(normalized)
			all_notes.extend(notes)
			profile.google_connected = True
			profile.auto_configured = bool(profile.gsc_property_url or profile.ga4_property_id)

		if provider in {'all', 'bing'} and bing_api.has_stored_tokens():
			profile, notes = await self._auto_discover_bing(normalized)
			all_notes.extend(notes)
			profile.bing_connected = bool(profile.bing_site_url)

		profile.discovery_notes = all_notes
		self._sites.save(profile)
		return profile

	async def _auto_discover_google(self, website_url: str) -> tuple[SeoSiteProfile, list[str]]:
		profile = self._sites.ensure(website_url)
		notes: list[str] = []
		creds = get_valid_credentials()

		if creds is not None:
			sites, site_deg = await gsc_list_sites(creds)
			notes.extend(site_deg)
			gsc_url, gsc_notes = pick_gsc_property(website_url, sites)
			notes.extend(gsc_notes)
			if gsc_url:
				profile.gsc_property_url = gsc_url
				notes.append(f'gsc_property_selected:{gsc_url}')

			props, ga4_deg = await google_api.ga4_list_properties(creds)
			notes.extend(ga4_deg)
			ga4_id, ga4_notes = pick_ga4_property(website_url, props)
			notes.extend(ga4_notes)
			if ga4_id:
				profile.ga4_property_id = ga4_id

		return profile, notes

	async def _auto_discover_bing(self, website_url: str) -> tuple[SeoSiteProfile, list[str]]:
		profile = self._sites.ensure(website_url)
		notes: list[str] = []
		if not bing_api.has_stored_tokens():
			return profile, ['bing_discovery:not_connected']
		sites, site_deg = await bing_api.bwm_get_user_sites()
		notes.extend(site_deg)
		bing_url, bing_notes = pick_bing_site(website_url, sites)
		notes.extend(bing_notes)
		if bing_url:
			profile.bing_site_url = bing_url
		return profile, notes

	async def _auto_discover(self, website_url: str) -> tuple[SeoSiteProfile, list[str]]:
		profile, notes = await self._auto_discover_google(website_url)
		if bing_api.has_stored_tokens():
			profile, bing_notes = await self._auto_discover_bing(website_url)
			notes.extend(bing_notes)
		return profile, notes

	def enrich_audit_request(self, request: SeoAuditRequest) -> tuple[SeoAuditRequest, SeoSiteProfile | None, list[str]]:
		notes: list[str] = []
		normalized = normalize_website_url(request.website_url)
		if not normalized:
			return request, None, ['website_url_invalid']

		profile = self._sites.get(normalized)

		property_url = request.property_url.strip()
		ga4_property_id = request.ga4_property_id.strip()
		bing_site_url = request.bing_site_url.strip()

		if profile is not None:
			if not property_url and profile.gsc_property_url:
				property_url = profile.gsc_property_url
			if not ga4_property_id and profile.ga4_property_id:
				ga4_property_id = profile.ga4_property_id
			if not bing_site_url and profile.bing_site_url:
				bing_site_url = profile.bing_site_url

		enriched = replace(
			request,
			website_url=normalized,
			property_url=property_url,
			ga4_property_id=ga4_property_id,
			bing_site_url=bing_site_url,
		)
		return enriched, profile, notes
