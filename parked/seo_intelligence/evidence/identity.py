"""Deterministic evidence identity — stable across audits (ADR-027)."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, urlunparse

from navigation.seo_intelligence.models import SeoEvidenceRef


def normalize_page_url(url: str, *, base_url: str = '') -> str:
	"""Canonical page URL for graph joins (path + host, no fragment)."""
	raw = (url or '').strip()
	if not raw:
		return ''
	if raw.startswith('/'):
		base = (base_url or '').strip().rstrip('/')
		if base:
			raw = f'{base}{raw}'
		else:
			return raw.lower().rstrip('/')
	parsed = urlparse(raw if '://' in raw else f'https://{raw}')
	if not parsed.netloc and not parsed.path:
		return ''
	normalized = urlunparse((
		(parsed.scheme or 'https').lower(),
		parsed.netloc.lower(),
		parsed.path.rstrip('/') or '/',
		'',
		'',
		'',
	))
	return normalized


def _norm_text(value: str) -> str:
	return re.sub(r'\s+', ' ', (value or '').strip().lower())


def stable_evidence_id(
	provider_id: str,
	kind: str,
	*,
	page_url: str = '',
	title: str = '',
	source_ref: str = '',
	metric_key: str = '',
	base_url: str = '',
) -> str:
	"""ev:{provider}:{kind}:{fingerprint} — same issue on same page → same ID."""
	page = normalize_page_url(page_url, base_url=base_url) if page_url else ''
	key = '|'.join([
		provider_id,
		kind,
		page,
		_norm_text(title),
		source_ref.strip(),
		metric_key.strip(),
	])
	fingerprint = hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]
	safe_kind = re.sub(r'[^a-z0-9_]+', '_', kind.lower())[:32]
	return f'ev:{provider_id}:{safe_kind}:{fingerprint}'


def page_url_for_evidence(item: SeoEvidenceRef, *, base_url: str = '') -> str:
	"""Resolved page URL used for graph joins."""
	if item.page_url:
		return normalize_page_url(item.page_url, base_url=base_url)
	if item.url and item.url.startswith('http'):
		return normalize_page_url(item.url, base_url=base_url)
	return normalize_page_url(item.url, base_url=base_url) if item.url else ''
