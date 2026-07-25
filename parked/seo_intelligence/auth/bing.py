"""Bing Webmaster Tools OAuth + API key auth (user-owned tokens, local storage)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from navigation.seo_intelligence.config.defaults import bing_oauth_redirect_uri, default_seo_cache_dir

BING_SCOPE = 'webmaster.read'
BING_AUTH_URL = 'https://www.bing.com/webmasters/oauth/authorize'
BING_TOKEN_URL = 'https://www.bing.com/webmasters/oauth/token'
BING_API_JSON = 'https://ssl.bing.com/webmaster/api.svc/json'

_TOKEN_VERSION = 1


def token_path() -> Path:
	raw = os.environ.get('SEO_BING_TOKEN_PATH', '').strip()
	if raw:
		return Path(raw)
	return default_seo_cache_dir() / 'seo_bing_tokens.json'


def redirect_uri() -> str:
	return bing_oauth_redirect_uri()


def bing_oauth_configured() -> bool:
	return bool(
		os.environ.get('BING_WEBMASTER_OAUTH_CLIENT_ID', '').strip()
		and os.environ.get('BING_WEBMASTER_OAUTH_CLIENT_SECRET', '').strip()
	)


def _client_id() -> str:
	return os.environ.get('BING_WEBMASTER_OAUTH_CLIENT_ID', '').strip()


def _client_secret() -> str:
	return os.environ.get('BING_WEBMASTER_OAUTH_CLIENT_SECRET', '').strip()


def build_authorization_url(*, redirect_uri_override: str | None = None) -> str:
	if not bing_oauth_configured():
		raise RuntimeError('bing_oauth_not_configured_by_operator')
	redirect = redirect_uri_override or redirect_uri()
	params = {
		'response_type': 'code',
		'client_id': _client_id(),
		'redirect_uri': redirect,
		'scope': BING_SCOPE,
	}
	return f'{BING_AUTH_URL}?{urlencode(params)}'


def exchange_authorization_code(code: str, *, redirect_uri_override: str | None = None) -> dict[str, Any]:
	if not bing_oauth_configured():
		raise RuntimeError('bing_oauth_not_configured_by_operator')
	redirect = redirect_uri_override or redirect_uri()
	body = {
		'client_id': _client_id(),
		'client_secret': _client_secret(),
		'code': code.strip(),
		'grant_type': 'authorization_code',
		'redirect_uri': redirect,
	}
	resp = httpx.post(BING_TOKEN_URL, data=body, timeout=30.0)
	resp.raise_for_status()
	payload = resp.json()
	expires_in = int(payload.get('expires_in') or 3600)
	_save_token_data(
		{
			'auth_mode': 'oauth',
			'access_token': str(payload.get('access_token') or ''),
			'refresh_token': str(payload.get('refresh_token') or ''),
			'token_type': str(payload.get('token_type') or 'Bearer'),
			'expires_at': time.time() + expires_in,
		}
	)
	return bing_auth_status()


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


def has_stored_tokens() -> bool:
	data = _load_token_data()
	if not data:
		return False
	if data.get('auth_mode') == 'api_key':
		return bool(str(data.get('api_key') or '').strip())
	return bool(str(data.get('access_token') or '').strip())


def store_api_key(api_key: str) -> dict[str, Any]:
	key = api_key.strip()
	if not key:
		raise ValueError('bing_api_key_required')
	_save_token_data({'auth_mode': 'api_key', 'api_key': key})
	return bing_auth_status()


def _refresh_access_token(data: dict[str, Any]) -> dict[str, Any] | None:
	refresh = str(data.get('refresh_token') or '').strip()
	if not refresh or not bing_oauth_configured():
		return None
	body = {
		'client_id': _client_id(),
		'client_secret': _client_secret(),
		'refresh_token': refresh,
		'grant_type': 'refresh_token',
	}
	try:
		resp = httpx.post(BING_TOKEN_URL, data=body, timeout=30.0)
		resp.raise_for_status()
		payload = resp.json()
	except Exception:
		return None
	expires_in = int(payload.get('expires_in') or 3600)
	updated = {
		**data,
		'auth_mode': 'oauth',
		'access_token': str(payload.get('access_token') or data.get('access_token') or ''),
		'token_type': str(payload.get('token_type') or data.get('token_type') or 'Bearer'),
		'expires_at': time.time() + expires_in,
	}
	if payload.get('refresh_token'):
		updated['refresh_token'] = str(payload['refresh_token'])
	_save_token_data(updated)
	return updated


def get_valid_access_token() -> tuple[str, str]:
	"""Return (access_token_or_api_key, auth_mode)."""
	data = _load_token_data()
	if not data:
		return '', ''
	if data.get('auth_mode') == 'api_key':
		return str(data.get('api_key') or '').strip(), 'api_key'
	access = str(data.get('access_token') or '').strip()
	if not access:
		return '', ''
	expires_at = float(data.get('expires_at') or 0)
	if expires_at and time.time() >= expires_at - 60:
		refreshed = _refresh_access_token(data)
		if refreshed:
			return str(refreshed.get('access_token') or '').strip(), 'oauth'
	return access, 'oauth'


def bing_auth_status() -> dict[str, Any]:
	data = _load_token_data() or {}
	return {
		'configured': bing_oauth_configured(),
		'has_tokens': has_stored_tokens(),
		'auth_mode': str(data.get('auth_mode') or ''),
		'token_path': str(token_path()),
		'scope': BING_SCOPE,
		'redirect_uri': redirect_uri(),
	}


def _site_profile(website_url: str):
	if not website_url.strip():
		return None
	try:
		from navigation.seo_intelligence.setup.discovery import normalize_website_url
		from navigation.seo_intelligence.setup.site_store import SeoSiteStore

		return SeoSiteStore().get(normalize_website_url(website_url))
	except Exception:
		return None


def resolve_bing_site_url(request_site: str, website_url: str) -> str:
	if request_site.strip():
		return request_site.strip()
	profile = _site_profile(website_url)
	if profile is not None and profile.bing_site_url.strip():
		return profile.bing_site_url.strip()
	return normalize_website_url(website_url) if website_url.strip() else ''


async def bwm_get_user_sites() -> tuple[list[dict[str, Any]], list[str]]:
	token, mode = get_valid_access_token()
	if not token:
		return [], ['bing_not_authenticated:connect_bing_first']
	url = f'{BING_API_JSON}/GetUserSites'
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			if mode == 'api_key':
				resp = await client.get(url, params={'apikey': token})
			else:
				resp = await client.get(url, headers={'Authorization': f'Bearer {token}'})
		if resp.status_code == 401:
			return [], ['bing_oauth_unauthorized:reconnect']
		resp.raise_for_status()
		payload = resp.json()
		sites = payload.get('d') if isinstance(payload, dict) else payload
		if not isinstance(sites, list):
			return [], ['bing_get_user_sites:invalid_payload']
		normalized: list[dict[str, Any]] = []
		for site in sites:
			if isinstance(site, dict):
				normalized.append(site)
		return normalized, []
	except Exception as exc:
		return [], [f'bing_get_user_sites_error:{type(exc).__name__}']


async def bwm_get_query_stats(site_url: str) -> tuple[dict[str, Any] | None, list[str]]:
	token, mode = get_valid_access_token()
	if not token:
		return None, ['bing_not_authenticated']
	url = f'{BING_API_JSON}/GetQueryStats'
	params = {'siteUrl': site_url}
	try:
		async with httpx.AsyncClient(timeout=45.0) as client:
			if mode == 'api_key':
				params['apikey'] = token
				resp = await client.get(url, params=params)
			else:
				resp = await client.get(url, params=params, headers={'Authorization': f'Bearer {token}'})
		if resp.status_code == 401:
			return None, ['bing_oauth_unauthorized']
		resp.raise_for_status()
		return resp.json(), []
	except Exception as exc:
		return None, [f'bing_get_query_stats_error:{type(exc).__name__}']


def normalize_website_url(url: str) -> str:
	from navigation.seo_intelligence.setup.discovery import normalize_website_url as _norm

	return _norm(url)
