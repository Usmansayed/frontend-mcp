"""On-demand provider auth — Professional mode only."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.auth import bing as bing_api
from navigation.seo_intelligence.auth.google import has_stored_tokens as has_google_tokens
from navigation.seo_intelligence.models import SeoAuditMode, SeoAuditRequest
from navigation.seo_intelligence.planning.capabilities import CAPABILITY_CATALOG
from navigation.seo_intelligence.planning.auth_constants import (
	BING_AUTH_INTENTS,
	BING_AUTH_PROVIDERS,
	GOOGLE_AUTH_INTENTS,
	GOOGLE_AUTH_PROVIDERS,
)


def _capabilities_for_request(request: SeoAuditRequest) -> list[str]:
	if request.intents:
		return [c for c in request.intents if c in CAPABILITY_CATALOG]
	return []


def providers_requiring_auth(request: SeoAuditRequest) -> dict[str, set[str]]:
	"""Return auth buckets needed: google | bing -> provider ids (Professional mode only)."""
	from navigation.seo_intelligence.planning.modes import capabilities_for_mode, resolve_effective_mode

	if resolve_effective_mode(request) != SeoAuditMode.PROFESSIONAL:
		return {'google': set(), 'bing': set()}

	needed: dict[str, set[str]] = {'google': set(), 'bing': set()}

	for pid in request.providers:
		if pid in GOOGLE_AUTH_PROVIDERS:
			needed['google'].add(pid)
		if pid in BING_AUTH_PROVIDERS:
			needed['bing'].add(pid)

	for cap_id in _capabilities_for_request(request):
		spec = CAPABILITY_CATALOG.get(cap_id)
		if spec is None:
			continue
		primary = spec.primary_provider
		if primary in GOOGLE_AUTH_PROVIDERS or cap_id in GOOGLE_AUTH_INTENTS:
			if primary in GOOGLE_AUTH_PROVIDERS:
				needed['google'].add(primary)
			else:
				needed['google'].add('search-console')
		if primary in BING_AUTH_PROVIDERS or cap_id in BING_AUTH_INTENTS:
			needed['bing'].add('bing-webmaster')

	for cap_id in request.intents:
		if cap_id in GOOGLE_AUTH_INTENTS:
			needed['google'].add('search-console')
		if cap_id in BING_AUTH_INTENTS:
			needed['bing'].add('bing-webmaster')

	mode = resolve_effective_mode(request)
	for cap_id in capabilities_for_mode(request, mode):
		spec = CAPABILITY_CATALOG.get(cap_id)
		if spec is None:
			continue
		if spec.primary_provider in GOOGLE_AUTH_PROVIDERS:
			needed['google'].add(spec.primary_provider)
		for fallback in spec.fallback_providers:
			if fallback in GOOGLE_AUTH_PROVIDERS:
				needed['google'].add(fallback)
			if fallback in BING_AUTH_PROVIDERS:
				needed['bing'].add(fallback)

	return needed


def auth_prompts_for_request(request: SeoAuditRequest) -> list[dict[str, Any]]:
	"""User-facing prompts when Professional mode needs OAuth but tokens are missing."""
	from navigation.seo_intelligence.planning.modes import resolve_effective_mode

	if resolve_effective_mode(request) != SeoAuditMode.PROFESSIONAL:
		return []

	needed = providers_requiring_auth(request)
	prompts: list[dict[str, Any]] = []

	if needed['google'] and not has_google_tokens():
		prompts.append(
			{
				'provider': 'google',
				'prompt': 'Connect your Google Search Console and Analytics to analyze live search data.',
				'connect': {
					'tool': 'perception_seo_connect',
					'website_url': request.website_url,
					'action': 'connect_google',
					'interactive': True,
				},
				'providers_needed': sorted(needed['google']),
				'mode': 'professional',
			}
		)

	if needed['bing'] and not bing_api.has_stored_tokens():
		prompts.append(
			{
				'provider': 'bing',
				'prompt': 'Connect your Bing Webmaster account.',
				'connect': {
					'tool': 'perception_seo_connect',
					'website_url': request.website_url,
					'provider': 'bing',
					'action': 'connect_bing',
					'interactive': True,
				},
				'providers_needed': sorted(needed['bing']),
				'mode': 'professional',
			}
		)

	return prompts


def audit_blocked_by_auth(request: SeoAuditRequest) -> bool:
	return bool(auth_prompts_for_request(request))
