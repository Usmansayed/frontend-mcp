"""SEO Intelligence onboarding tests."""

from __future__ import annotations



import sys

import tempfile

from pathlib import Path

from unittest.mock import AsyncMock, patch



ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / 'src'

sys.path.insert(0, str(SRC))



from navigation.seo_intelligence import SeoAuditRequest

from navigation.seo_intelligence.config.defaults import (

	DEFAULT_LIBRECRAWL_BASE_URL,

	bundled_librecrawl_base_url,

)

from navigation.seo_intelligence.setup.discovery import (

	domain_from_website,

	normalize_website_url,

	pick_bing_site,

	pick_ga4_property,

	pick_gsc_property,

)

from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

from navigation.seo_intelligence.setup.site_store import SeoSiteProfile, SeoSiteStore





def test_normalize_website_url() -> None:

	assert normalize_website_url('example.com') == 'https://example.com/'

	assert domain_from_website('https://www.example.com/path') == 'example.com'





def test_pick_gsc_property_prefers_domain_property() -> None:

	sites = [

		{'siteUrl': 'https://other.com/'},

		{'siteUrl': 'sc-domain:example.com'},

		{'siteUrl': 'https://example.com/'},

	]

	url, notes = pick_gsc_property('https://example.com', sites)

	assert url == 'sc-domain:example.com'

	assert isinstance(notes, list)





def test_pick_ga4_property_matches_display_name() -> None:

	props = [

		{'name': 'properties/111', 'displayName': 'Other Site'},

		{'name': 'properties/222', 'displayName': 'example.com marketing'},

	]

	prop_id, _ = pick_ga4_property('https://example.com', props)

	assert prop_id == 'properties/222'





def test_bundled_service_defaults_without_env() -> None:

	with patch.dict('os.environ', {}, clear=True):

		assert bundled_librecrawl_base_url() == DEFAULT_LIBRECRAWL_BASE_URL





def test_site_store_roundtrip() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		profile = SeoSiteProfile(

			website_url='https://example.com/',

			domain='example.com',

			gsc_property_url='sc-domain:example.com',

			ga4_property_id='properties/123',

			google_connected=True,

			auto_configured=True,

		)

		store.save(profile)

		loaded = store.get('https://example.com')

		assert loaded is not None

		assert loaded.gsc_property_url == 'sc-domain:example.com'

		assert loaded.ga4_property_id == 'properties/123'





def test_enrich_audit_request_includes_bing_site() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		store.save(

			SeoSiteProfile(

				website_url='https://example.com/',

				domain='example.com',

				bing_site_url='https://example.com/',

				bing_connected=True,

			)

		)

		onboarding = SeoOnboardingService(site_store=store)

		request = SeoAuditRequest(website_url='example.com')

		enriched, profile, notes = onboarding.enrich_audit_request(request)

		assert profile is not None

		assert enriched.bing_site_url == 'https://example.com/'

		assert notes == []





def test_enrich_audit_request_from_profile() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		store.save(

			SeoSiteProfile(

				website_url='https://example.com/',

				domain='example.com',

				gsc_property_url='sc-domain:example.com',

				ga4_property_id='properties/999',

			)

		)

		onboarding = SeoOnboardingService(site_store=store)

		request = SeoAuditRequest(website_url='example.com')

		enriched, profile, notes = onboarding.enrich_audit_request(request)

		assert profile is not None

		assert enriched.property_url == 'sc-domain:example.com'

		assert enriched.ga4_property_id == 'properties/999'

		assert notes == []





def test_complete_google_connect_auto_discovers() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		onboarding = SeoOnboardingService(site_store=store)



		mock_creds = object()

		with (

			patch('navigation.seo_intelligence.setup.onboarding.exchange_google_authorization_code'),

			patch('navigation.seo_intelligence.setup.onboarding.get_valid_credentials', return_value=mock_creds),

			patch(

				'navigation.seo_intelligence.setup.onboarding.gsc_list_sites',

				new=AsyncMock(

					return_value=([{'siteUrl': 'sc-domain:example.com'}], []),

				),

			),

			patch(

				'navigation.seo_intelligence.setup.onboarding.google_api.ga4_list_properties',

				new=AsyncMock(

					return_value=([{'name': 'properties/555', 'displayName': 'example.com'}], []),

				),

			),

		):

			result = asyncio_run(onboarding.complete_google_connect('https://example.com', 'auth-code'))

		profile = result['profile']

		assert profile['google_connected'] is True

		assert profile['gsc_property_url'] == 'sc-domain:example.com'

		assert profile['ga4_property_id'] == 'properties/555'





def test_register_website_only() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		onboarding = SeoOnboardingService(site_store=store)

		result = asyncio_run(onboarding.register_website('https://strikeloop.com'))

		assert result['ready'] is True

		assert result['step'] == 'registered'

		status = asyncio_run(onboarding.site_status('https://strikeloop.com'))

		assert status['ready'] is True

		assert status['auth_on_demand'] is True

		assert status['google_connected'] is False





def test_auth_required_for_gsc_intent_in_professional_mode() -> None:
	from navigation.seo_intelligence import SeoAuditRequest
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.setup.auth_requirements import audit_blocked_by_auth, auth_prompts_for_request

	request = SeoAuditRequest(
		website_url='https://strikeloop.com',
		intents=['search_queries'],
		mode=SeoAuditMode.PROFESSIONAL,
	)
	with patch('navigation.seo_intelligence.setup.auth_requirements.has_google_tokens', return_value=False):
		assert audit_blocked_by_auth(request) is True
		prompts = auth_prompts_for_request(request)
		assert prompts[0]['provider'] == 'google'
		assert 'Search Console' in prompts[0]['prompt']


def test_development_mode_never_blocks_auth() -> None:
	from navigation.seo_intelligence import SeoAuditRequest
	from navigation.seo_intelligence.models import SeoAuditMode
	from navigation.seo_intelligence.setup.auth_requirements import audit_blocked_by_auth

	request = SeoAuditRequest(
		website_url='https://strikeloop.com',
		intents=['search_queries'],
		mode=SeoAuditMode.DEVELOPMENT,
	)
	with patch('navigation.seo_intelligence.setup.auth_requirements.has_google_tokens', return_value=False):
		assert audit_blocked_by_auth(request) is False


def test_default_audit_not_blocked_without_google() -> None:

	from navigation.seo_intelligence import SeoAuditRequest

	from navigation.seo_intelligence.setup.auth_requirements import audit_blocked_by_auth



	request = SeoAuditRequest(website_url='https://strikeloop.com')

	with patch('navigation.seo_intelligence.setup.auth_requirements.has_google_tokens', return_value=False):

		assert audit_blocked_by_auth(request) is False





def test_pick_bing_site_matches_domain() -> None:

	sites = [

		{'Url': 'https://other.com/', 'IsVerified': True},

		{'Url': 'https://example.com/', 'IsVerified': True},

	]

	url, _ = pick_bing_site('https://example.com', sites)

	assert url == 'https://example.com/'





def test_complete_bing_api_key_discovers_site() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		onboarding = SeoOnboardingService(site_store=store)

		with (

			patch('navigation.seo_intelligence.setup.onboarding.bing_api.store_api_key'),

			patch('navigation.seo_intelligence.setup.onboarding.bing_api.has_stored_tokens', return_value=True),

			patch(

				'navigation.seo_intelligence.setup.onboarding.bing_api.bwm_get_user_sites',

				new=AsyncMock(

					return_value=([{'Url': 'https://example.com/', 'IsVerified': True}], []),

				),

			),

		):

			result = asyncio_run(onboarding.complete_bing_api_key('https://example.com', 'bing-key'))

		profile = result['profile']

		assert profile['bing_connected'] is True

		assert profile['bing_site_url'] == 'https://example.com/'





def test_site_status_ready_without_google() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		store.save(

			SeoSiteProfile(

				website_url='https://example.com/',

				domain='example.com',

			)

		)

		onboarding = SeoOnboardingService(site_store=store)

		status = asyncio_run(onboarding.site_status('https://example.com'))

		assert status['ready'] is True

		assert status['google_connected'] is False





def test_resolve_gsc_property_uses_site_store() -> None:

	with tempfile.TemporaryDirectory() as tmp:

		store = SeoSiteStore(path=Path(tmp) / 'seo_sites.json')

		store.save(

			SeoSiteProfile(

				website_url='https://example.com/',

				domain='example.com',

				gsc_property_url='sc-domain:example.com',

			)

		)

		with patch('navigation.seo_intelligence.setup.site_store.SeoSiteStore', return_value=store):

			from navigation.seo_intelligence.auth.google import resolve_gsc_property



			assert resolve_gsc_property('', 'https://example.com') == 'sc-domain:example.com'





def asyncio_run(coro):

	import asyncio



	return asyncio.run(coro)


