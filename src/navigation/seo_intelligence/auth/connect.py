"""Browser-based OAuth connect workflows for SEO Intelligence."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.auth import bing as bing_api
from navigation.seo_intelligence.auth import google as google_api
from navigation.seo_intelligence.auth.local_server import run_browser_oauth
from navigation.seo_intelligence.config.defaults import (
	bing_oauth_redirect_uri,
	google_oauth_redirect_uri,
	oauth_callback_parts_from_redirect_uri,
)
from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService


async def connect_google(
	website_url: str,
	*,
	open_browser: bool = True,
	onboarding: SeoOnboardingService | None = None,
) -> dict[str, Any]:
	"""Open browser → Google OAuth → store tokens → auto-discover GSC + GA4."""
	if not google_api.google_oauth_configured():
		raise RuntimeError('google_oauth_not_configured_by_operator')
	redirect_uri = google_oauth_redirect_uri()
	callback_path, port = oauth_callback_parts_from_redirect_uri(redirect_uri)
	auth_url = google_api.build_authorization_url(redirect_uri=redirect_uri)
	code, used_redirect = await run_browser_oauth(
		authorization_url=auth_url,
		callback_path=callback_path,
		port=port,
		open_browser=open_browser,
	)
	service = onboarding or SeoOnboardingService()
	result = await service.complete_google_connect(
		website_url,
		code,
		redirect_uri=used_redirect,
	)
	result['auth_flow'] = 'local_browser_oauth'
	result['redirect_uri'] = used_redirect
	return result


async def connect_bing(
	website_url: str,
	*,
	open_browser: bool = True,
	onboarding: SeoOnboardingService | None = None,
) -> dict[str, Any]:
	"""Open browser → Bing OAuth → store tokens → auto-discover Bing sites."""
	if not bing_api.bing_oauth_configured():
		raise RuntimeError('bing_oauth_not_configured_by_operator')
	redirect_uri = bing_oauth_redirect_uri()
	auth_url = bing_api.build_authorization_url(redirect_uri_override=redirect_uri)
	code, used_redirect = await run_browser_oauth(
		authorization_url=auth_url,
		callback_path='/bing/callback',
		open_browser=open_browser,
	)
	service = onboarding or SeoOnboardingService()
	result = await service.complete_bing_connect(
		website_url,
		code,
		redirect_uri=used_redirect,
	)
	result['auth_flow'] = 'local_browser_oauth'
	result['redirect_uri'] = used_redirect
	return result
