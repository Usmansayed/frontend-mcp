"""SEO audit modes — Development (default) vs Professional optimization."""
from __future__ import annotations

from urllib.parse import urlparse

from navigation.seo_intelligence.models import SeoAuditMode, SeoAuditRequest
from navigation.seo_intelligence.planning.capabilities import (
	CAPABILITY_CATALOG,
	DEVELOPMENT_AUDIT_CAPABILITIES,
	PROFESSIONAL_AUDIT_CAPABILITIES,
)
from navigation.seo_intelligence.planning.auth_constants import (
	BING_AUTH_INTENTS,
	BING_AUTH_PROVIDERS,
	GOOGLE_AUTH_INTENTS,
	GOOGLE_AUTH_PROVIDERS,
)

# Development: browser scan + derived AI visibility only (no crawl, lighthouse, or auth).
DEVELOPMENT_PROVIDERS = frozenset({'browser'})
PROFESSIONAL_PROVIDERS = frozenset({'librecrawl', 'lighthouse', 'browser'}) | GOOGLE_AUTH_PROVIDERS | BING_AUTH_PROVIDERS

_PROFESSIONAL_MODE_ALIASES = frozenset({'professional', 'pro', 'optimization', 'optimize'})
_LOCAL_HOSTS = frozenset({'localhost', '127.0.0.1', '::1', '[::1]'})


def is_local_dev_url(url: str) -> bool:
	"""True for localhost / loopback — defaults to fast Development SEO."""
	try:
		host = (urlparse(url).hostname or '').lower()
	except ValueError:
		return False
	return host in _LOCAL_HOSTS or host.endswith('.localhost')


def parse_audit_mode(raw: str) -> SeoAuditMode:
	value = (raw or 'development').strip().lower()
	if value in _PROFESSIONAL_MODE_ALIASES:
		return SeoAuditMode.PROFESSIONAL
	return SeoAuditMode.DEVELOPMENT


def resolve_effective_mode(request: SeoAuditRequest) -> SeoAuditMode:
	"""Development is default; localhost forces development unless mode=professional."""
	if request.mode == SeoAuditMode.PROFESSIONAL:
		return SeoAuditMode.PROFESSIONAL
	if request.mode == SeoAuditMode.DEVELOPMENT:
		return SeoAuditMode.DEVELOPMENT

	for pid in request.providers:
		if pid in GOOGLE_AUTH_PROVIDERS | BING_AUTH_PROVIDERS:
			return SeoAuditMode.PROFESSIONAL

	for intent in request.intents:
		if intent in GOOGLE_AUTH_INTENTS | BING_AUTH_INTENTS:
			return SeoAuditMode.PROFESSIONAL
		spec = CAPABILITY_CATALOG.get(intent)
		if spec is not None and spec.primary_provider in GOOGLE_AUTH_PROVIDERS | BING_AUTH_PROVIDERS:
			return SeoAuditMode.PROFESSIONAL

	if is_local_dev_url(request.website_url):
		return SeoAuditMode.DEVELOPMENT

	return SeoAuditMode.DEVELOPMENT


def capabilities_for_mode(request: SeoAuditRequest, mode: SeoAuditMode) -> list[str]:
	if request.intents:
		caps = [c for c in request.intents if c in CAPABILITY_CATALOG]
		if mode == SeoAuditMode.DEVELOPMENT:
			allowed = set(DEVELOPMENT_AUDIT_CAPABILITIES)
			caps = [c for c in caps if c in allowed]
		return caps

	caps = list(
		PROFESSIONAL_AUDIT_CAPABILITIES if mode == SeoAuditMode.PROFESSIONAL else DEVELOPMENT_AUDIT_CAPABILITIES
	)
	if request.scan_id and 'rendering_verification' not in caps:
		caps.append('rendering_verification')
	return caps


def provider_allowed(provider_id: str, mode: SeoAuditMode) -> bool:
	if mode == SeoAuditMode.DEVELOPMENT:
		return provider_id in DEVELOPMENT_PROVIDERS
	return provider_id in PROFESSIONAL_PROVIDERS


def mode_summary(mode: SeoAuditMode) -> dict[str, object]:
	if mode == SeoAuditMode.PROFESSIONAL:
		return {
			'mode': mode.value,
			'display_name': 'Professional SEO Optimization',
			'auth_required_for_google': True,
			'providers': sorted(PROFESSIONAL_PROVIDERS),
			'description': 'Live search data (GSC, GA4) combined with technical evidence for optimization.',
			'instant': False,
			'async_job': True,
		}
	return {
		'mode': mode.value,
		'display_name': 'Development SEO',
		'auth_required_for_google': False,
		'providers': sorted(DEVELOPMENT_PROVIDERS),
		'description': (
			'Instant engineering assistant from browser scan — metadata, semantics, '
			'headings, schema hints, a11y, and AI visibility. No crawl or auth.'
		),
		'instant': True,
		'requires_scan_id': True,
	}
