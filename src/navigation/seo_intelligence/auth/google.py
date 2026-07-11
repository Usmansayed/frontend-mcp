"""Google OAuth for Search Console + GA4 (user-owned tokens, local storage)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

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


def _client_config() -> dict[str, Any]:
	client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()
	client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
	return {
		'installed': {
			'client_id': client_id,
			'client_secret': client_secret,
			'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
			'token_uri': 'https://oauth2.googleapis.com/token',
			'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob', 'http://localhost'],
		}
	}


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
	creds = Credentials.from_authorized_user_info(data, GOOGLE_SCOPES)
	if creds.expired and creds.refresh_token:
		creds.refresh(Request())
		_save_token_data(json.loads(creds.to_json()))
	return creds


def build_authorization_url(*, redirect_uri: str = 'urn:ietf:wg:oauth:2.0:oob') -> str:
	if not google_oauth_configured():
		raise RuntimeError('google_oauth_not_configured')
	from google_auth_oauthlib.flow import Flow

	flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_SCOPES, redirect_uri=redirect_uri)
	auth_url, _ = flow.authorization_url(
		access_type='offline',
		include_granted_scopes='true',
		prompt='consent',
	)
	return auth_url


def exchange_authorization_code(code: str, *, redirect_uri: str = 'urn:ietf:wg:oauth:2.0:oob') -> dict[str, Any]:
	if not google_oauth_configured():
		raise RuntimeError('google_oauth_not_configured')
	from google_auth_oauthlib.flow import Flow

	flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_SCOPES, redirect_uri=redirect_uri)
	flow.fetch_token(code=code.strip())
	creds = flow.credentials
	_save_token_data(json.loads(creds.to_json()))
	return google_oauth_status()


def google_oauth_status() -> dict[str, Any]:
	return {
		'configured': google_oauth_configured(),
		'has_tokens': has_stored_tokens(),
		'token_path': str(token_path()),
		'scopes': list(GOOGLE_SCOPES),
	}


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
		resp.raise_for_status()
		payload = resp.json()
		return list(payload.get('siteEntry') or []), degraded
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
		if resp.status_code == 403:
			return None, ['gsc_permission_denied:check_property_access']
		resp.raise_for_status()
		return resp.json(), []
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
		if resp.status_code == 403:
			return None, ['gsc_inspection_permission_denied']
		resp.raise_for_status()
		return resp.json(), []
	except Exception as exc:
		return None, [f'gsc_inspect_url_error:{type(exc).__name__}']


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
		if resp.status_code == 403:
			return None, ['ga4_permission_denied:check_property_access']
		resp.raise_for_status()
		return resp.json(), []
	except Exception as exc:
		return None, [f'ga4_run_report_error:{type(exc).__name__}']


def default_date_range(days: int = 28) -> tuple[str, str]:
	from datetime import date, timedelta

	end = date.today() - timedelta(days=3)
	start = end - timedelta(days=days - 1)
	return start.isoformat(), end.isoformat()


def resolve_gsc_property(request_property: str, website_url: str) -> str:
	if request_property.strip():
		return request_property.strip()
	if website_url.strip():
		from urllib.parse import urlparse

		parsed = urlparse(website_url.strip())
		if parsed.scheme and parsed.netloc:
			return f'{parsed.scheme}://{parsed.netloc}/'
	return ''


def resolve_ga4_property_id(request_property: str) -> str:
	return (
		request_property.strip()
		or os.environ.get('GA4_PROPERTY_ID', '').strip()
		or os.environ.get('GOOGLE_ANALYTICS_PROPERTY_ID', '').strip()
	)
