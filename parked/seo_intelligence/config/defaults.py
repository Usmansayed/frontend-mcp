"""Bundled service defaults — operators override via env; users never configure these."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# Self-hosted LibreCrawl — native process, auto-started before audits.
DEFAULT_LIBRECRAWL_BASE_URL = 'http://localhost:5001'
DEFAULT_SEO_CACHE_DIR = '.cache'
DEFAULT_OAUTH_CALLBACK_HOST = '127.0.0.1'
DEFAULT_OAUTH_CALLBACK_PORT = 8787
DEFAULT_GOOGLE_OAUTH_REDIRECT_URI = 'http://localhost:5000/api/auth/google/callback'


def default_seo_cache_dir() -> Path:
	raw = os.environ.get('SEO_CACHE_DIR', DEFAULT_SEO_CACHE_DIR).strip() or DEFAULT_SEO_CACHE_DIR
	return Path(raw)


def bundled_librecrawl_base_url() -> str:
	return (
		os.environ.get('LIBRECRAWL_BASE_URL', '').strip()
		or os.environ.get('SEO_LIBRECRAWL_BASE_URL', '').strip()
		or DEFAULT_LIBRECRAWL_BASE_URL
	).rstrip('/')


def oauth_callback_host() -> str:
	return os.environ.get('SEO_OAUTH_CALLBACK_HOST', DEFAULT_OAUTH_CALLBACK_HOST).strip() or DEFAULT_OAUTH_CALLBACK_HOST


def oauth_callback_port() -> int:
	raw = os.environ.get('SEO_OAUTH_CALLBACK_PORT', '').strip()
	if raw:
		try:
			return max(1, min(65535, int(raw)))
		except ValueError:
			pass
	return DEFAULT_OAUTH_CALLBACK_PORT


def google_oauth_redirect_uri() -> str:
	override = os.environ.get('GOOGLE_OAUTH_REDIRECT_URI', '').strip()
	if override:
		return override
	return DEFAULT_GOOGLE_OAUTH_REDIRECT_URI


def oauth_callback_parts_from_redirect_uri(redirect_uri: str) -> tuple[str, int]:
	"""Return (callback_path, bind_port) parsed from a full redirect URI."""
	parsed = urlparse(redirect_uri)
	path = parsed.path or '/'
	if parsed.port is not None:
		port = parsed.port
	elif parsed.hostname in ('localhost', '127.0.0.1'):
		port = oauth_callback_port()
	else:
		port = 443 if parsed.scheme == 'https' else 80
	return path, port


def bing_oauth_redirect_uri() -> str:
	override = os.environ.get('BING_WEBMASTER_OAUTH_REDIRECT_URI', '').strip()
	if override:
		return override
	port = oauth_callback_port()
	return f'http://localhost:{port}/bing/callback'
