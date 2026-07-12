"""Google OAuth for Search Console + GA4 (user-owned tokens, local storage)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from urllib.parse import urlparse

from navigation.seo_intelligence.config.defaults import google_oauth_redirect_uri

GSC_SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
GA4_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
GOOGLE_SCOPES = [GSC_SCOPE, GA4_SCOPE]

_TOKEN_VERSION = 1


def token_path() -> Path:
	raw = os.environ.get('SEO_GOOGLE_TOKEN_PATH', '.cache/seo_google_tokens.json').strip()
	return Path(raw)


def google_oauth_configured() -> bool:
	return bool(
		os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()
		and os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
	)


def _oauth_client_type() -> str:
	"""Web clients use explicit redirect URIs; installed/desktop use loopback."""
	explicit = os.environ.get('GOOGLE_OAUTH_CLIENT_TYPE', '').strip().lower()
	if explicit in {'web', 'installed'}:
		return explicit
	redirect = google_oauth_redirect_uri()
	if '/api/auth/' in redirect:
		return 'web'
	parsed = urlparse(redirect)
	if parsed.port and parsed.port != 8787:
		return 'web'
	return 'installed'


def _client_config() -> dict[str, Any]:
	client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()
	client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
	redirect = google_oauth_redirect_uri()
	entry: dict[str, Any] = {
		'client_id': client_id,
		'client_secret': client_secret,
		'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
		'token_uri': 'https://oauth2.googleapis.com/token',
	}
	client_type = _oauth_client_type()
	if client_type == 'web':
		parsed = urlparse(redirect)
		origin = f'{parsed.scheme}://{parsed.hostname}'
		if parsed.port:
			origin = f'{origin}:{parsed.port}'
		entry['redirect_uris'] = [redirect]
		entry['javascript_origins'] = [origin]
	else:
		entry['redirect_uris'] = [redirect, 'http://localhost']
	return {client_type: entry}


def has_stored_tokens() -> bool:
	path = token_path()
	if not path.is_file():
		return False
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
	except json.JSONDecodeError:
		return False
	return bool(data.get('token'))


def _load_token_data() -> dict[str, Any] | None:
	path = token_path()
	if not path.is_file():
		return None
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
	except json.JSONDecodeError:
		return None
	return data if isinstance(data, dict) else None


def _save_token_data(data: dict[str, Any]) -> None:
	path = token_path()
	path.parent.mkdir(parents=True, exist_ok=True)
	payload = {'version': _TOKEN_VERSION, **data}
	path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def get_valid_credentials():
	"""Return refreshed google.oauth2.credentials.Credentials or None."""
	from google.auth.transport.requests import Request
	from google.oauth2.credentials import Credentials

	data = _load_token_data()
	if not data or not data.get('token'):
		return None
	granted = data.get('scopes')
	scope_list = [str(s) for s in granted] if isinstance(granted, list) and granted else GOOGLE_SCOPES
	creds = Credentials.from_authorized_user_info(data, scope_list)
	if creds.expired and creds.refresh_token:
		creds.refresh(Request())
		_save_token_data(json.loads(creds.to_json()))
	return creds


def build_authorization_url(*, redirect_uri: str | None = None) -> str:
	if not google_oauth_configured():
		raise RuntimeError('google_oauth_not_configured')
	from google_auth_oauthlib.flow import Flow

	redirect = redirect_uri or google_oauth_redirect_uri()
	flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_SCOPES, redirect_uri=redirect)
	auth_url, _ = flow.authorization_url(
		access_type='offline',
		prompt='consent',
	)
	return auth_url


def exchange_authorization_code(code: str, *, redirect_uri: str | None = None) -> dict[str, Any]:
	if not google_oauth_configured():
		raise RuntimeError('google_oauth_not_configured')
	from google_auth_oauthlib.flow import Flow

	# Web OAuth clients may return openid/userinfo scopes alongside requested scopes.
	os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')
	redirect = redirect_uri or google_oauth_redirect_uri()
	flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_SCOPES, redirect_uri=redirect)
	flow.fetch_token(code=code.strip())
	creds = flow.credentials
	_save_token_data(json.loads(creds.to_json()))
	return google_oauth_status()


def google_oauth_status() -> dict[str, Any]:
	data = _load_token_data() or {}
	granted = data.get('scopes')
	if isinstance(granted, list):
		granted_scopes = [str(s) for s in granted]
	else:
		granted_scopes = []
	return {
		'configured': google_oauth_configured(),
		'has_tokens': has_stored_tokens(),
		'token_path': str(token_path()),
		'requested_scopes': list(GOOGLE_SCOPES),
		'granted_scopes': granted_scopes,
		'has_gsc_scope': GSC_SCOPE in granted_scopes,
		'has_ga4_scope': GA4_SCOPE in granted_scopes,
		'redirect_uri': google_oauth_redirect_uri(),
		'client_type': _oauth_client_type(),
	}


def _google_api_error(resp: httpx.Response, *, prefix: str) -> str:
	"""Structured API error for degraded notes (status + reason + short message)."""
	try:
		payload = resp.json()
		err = payload.get('error') if isinstance(payload, dict) else {}
		if not isinstance(err, dict):
			err = {}
		code = err.get('code') or resp.status_code
		errors = err.get('errors') if isinstance(err.get('errors'), list) else []
		reason = ''
		if errors and isinstance(errors[0], dict):
			reason = str(errors[0].get('reason') or '')
		details = err.get('details') if isinstance(err.get('details'), list) else []
		detail_reason = ''
		for item in details:
			if isinstance(item, dict) and item.get('reason'):
				detail_reason = str(item['reason'])
				break
		message = str(err.get('message') or resp.text[:240]).replace('\n', ' ')
		parts = [prefix, f'http_{code}']
		if reason:
			parts.append(reason)
		if detail_reason and detail_reason != reason:
			parts.append(detail_reason)
		if 'searchconsole' in message.lower() and ('disabled' in message.lower() or 'not been used' in message.lower()):
			parts.append('enable_search_console_api_in_google_cloud')
		if 'analyticsadmin' in message.lower():
			parts.append('enable_analytics_admin_api_in_google_cloud')
		parts.append(message[:180])
		return ':'.join(parts)
	except Exception:
		return f'{prefix}:http_{resp.status_code}:{resp.text[:120]}'


def auth_headers(creds) -> dict[str, str]:
	if creds.token is None:
		raise RuntimeError('google_oauth_token_missing')
	return {'Authorization': f'Bearer {creds.token}'}


def encode_site_url(site_url: str) -> str:
	return quote(site_url, safe='')


async def gsc_list_sites(creds) -> tuple[list[dict[str, Any]], list[str]]:
	degraded: list[str] = []
	url = 'https://www.googleapis.com/webmasters/v3/sites'
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			resp = await client.get(url, headers=auth_headers(creds))
		if resp.status_code == 401:
			return [], ['google_oauth_unauthorized:refresh_or_reconnect']
		if resp.status_code >= 400:
			return [], [_google_api_error(resp, prefix='gsc_list_sites')]
		payload = resp.json()
		sites = list(payload.get('siteEntry') or [])
		if sites:
			degraded.append(f'gsc_sites_listed:{len(sites)}')
			for entry in sites:
				site_url = str(entry.get('siteUrl') or '')
				level = str(entry.get('permissionLevel') or '')
				if site_url:
					degraded.append(f'gsc_site:{site_url}:{level}')
		return sites, degraded
	except httpx.HTTPError as exc:
		return [], [f'gsc_list_sites_error:{type(exc).__name__}:{exc}']
	except Exception as exc:
		return [], [f'gsc_list_sites_error:{type(exc).__name__}']


async def gsc_search_analytics(
	creds,
	*,
	site_url: str,
	start_date: str,
	end_date: str,
	dimensions: list[str],
	row_limit: int = 50,
) -> tuple[dict[str, Any] | None, list[str]]:
	encoded = encode_site_url(site_url)
	url = f'https://www.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query'
	body = {
		'startDate': start_date,
		'endDate': end_date,
		'dimensions': dimensions,
		'rowLimit': row_limit,
	}
	try:
		async with httpx.AsyncClient(timeout=45.0) as client:
			resp = await client.post(url, headers=auth_headers(creds), json=body)
		if resp.status_code == 401:
			return None, ['google_oauth_unauthorized']
		if resp.status_code >= 400:
			return None, [_google_api_error(resp, prefix='gsc_search_analytics')]
		return resp.json(), []
	except httpx.HTTPError as exc:
		return None, [f'gsc_search_analytics_error:{type(exc).__name__}:{exc}']
	except Exception as exc:
		return None, [f'gsc_search_analytics_error:{type(exc).__name__}']


async def gsc_inspect_url(
	creds,
	*,
	site_url: str,
	inspection_url: str,
) -> tuple[dict[str, Any] | None, list[str]]:
	url = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
	body = {
		'inspectionUrl': inspection_url,
		'siteUrl': site_url,
	}
	try:
		async with httpx.AsyncClient(timeout=45.0) as client:
			resp = await client.post(url, headers=auth_headers(creds), json=body)
		if resp.status_code == 401:
			return None, ['google_oauth_unauthorized']
		if resp.status_code >= 400:
			return None, [_google_api_error(resp, prefix='gsc_inspect_url')]
		return resp.json(), []
	except httpx.HTTPError as exc:
		return None, [f'gsc_inspect_url_error:{type(exc).__name__}:{exc}']
	except Exception as exc:
		return None, [f'gsc_inspect_url_error:{type(exc).__name__}']


async def ga4_list_properties(creds) -> tuple[list[dict[str, Any]], list[str]]:
	"""List GA4 properties via Admin API accountSummaries."""
	degraded: list[str] = []
	url = 'https://analyticsadmin.googleapis.com/v1beta/accountSummaries'
	properties: list[dict[str, Any]] = []
	try:
		async with httpx.AsyncClient(timeout=45.0) as client:
			page_token: str | None = None
			while True:
				params: dict[str, Any] = {'pageSize': 200}
				if page_token:
					params['pageToken'] = page_token
				resp = await client.get(url, headers=auth_headers(creds), params=params)
				if resp.status_code == 401:
					return [], ['google_oauth_unauthorized']
				if resp.status_code >= 400:
					return [], [_google_api_error(resp, prefix='ga4_list_properties')]
				payload = resp.json()
				for account in payload.get('accountSummaries') or []:
					for prop in account.get('propertySummaries') or []:
						if not isinstance(prop, dict):
							continue
						properties.append(
							{
								'name': str(prop.get('property') or ''),
								'displayName': str(prop.get('displayName') or ''),
								'propertyType': str(prop.get('propertyType') or ''),
								'parent': str(account.get('account') or ''),
							}
						)
				page_token = payload.get('nextPageToken')
				if not page_token:
					break
		return properties, degraded
	except Exception as exc:
		return [], [f'ga4_list_properties_error:{type(exc).__name__}']


async def ga4_run_report(
	creds,
	*,
	property_id: str,
	start_date: str,
	end_date: str,
) -> tuple[dict[str, Any] | None, list[str]]:
	prop = property_id.removeprefix('properties/')
	api_url = f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport'
	body = {
		'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
		'dimensions': [{'name': 'landingPage'}, {'name': 'sessionDefaultChannelGroup'}],
		'metrics': [
			{'name': 'sessions'},
			{'name': 'activeUsers'},
			{'name': 'conversions'},
			{'name': 'engagementRate'},
		],
		'limit': 50,
		'orderBys': [{'metric': {'metricName': 'sessions'}, 'desc': True}],
	}
	try:
		async with httpx.AsyncClient(timeout=45.0) as client:
			resp = await client.post(api_url, headers=auth_headers(creds), json=body)
		if resp.status_code == 401:
			return None, ['google_oauth_unauthorized']
		if resp.status_code >= 400:
			return None, [_google_api_error(resp, prefix='ga4_run_report')]
		return resp.json(), []
	except httpx.HTTPError as exc:
		return None, [f'ga4_run_report_error:{type(exc).__name__}:{exc}']
	except Exception as exc:
		return None, [f'ga4_run_report_error:{type(exc).__name__}']


def default_date_range(days: int = 28) -> tuple[str, str]:
	from datetime import date, timedelta

	end = date.today() - timedelta(days=3)
	start = end - timedelta(days=days - 1)
	return start.isoformat(), end.isoformat()


def _site_profile(website_url: str):
	if not website_url.strip():
		return None
	try:
		from navigation.seo_intelligence.setup.discovery import normalize_website_url
		from navigation.seo_intelligence.setup.site_store import SeoSiteStore

		return SeoSiteStore().get(normalize_website_url(website_url))
	except Exception:
		return None


def resolve_gsc_property(request_property: str, website_url: str) -> str:
	if request_property.strip():
		return request_property.strip()
	profile = _site_profile(website_url)
	if profile is not None and profile.gsc_property_url.strip():
		return profile.gsc_property_url.strip()
	if website_url.strip():
		from urllib.parse import urlparse

		parsed = urlparse(website_url.strip())
		if parsed.scheme and parsed.netloc:
			return f'{parsed.scheme}://{parsed.netloc}/'
	return ''


def resolve_ga4_property_id(request_property: str, website_url: str = '') -> str:
	if request_property.strip():
		return request_property.strip()
	profile = _site_profile(website_url)
	if profile is not None and profile.ga4_property_id.strip():
		return profile.ga4_property_id.strip()
	return (
		os.environ.get('GA4_PROPERTY_ID', '').strip()
		or os.environ.get('GOOGLE_ANALYTICS_PROPERTY_ID', '').strip()
	)
