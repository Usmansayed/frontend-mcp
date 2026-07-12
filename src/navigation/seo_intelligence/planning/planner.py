"""SEO audit planner — orchestrates evidence providers only (no SEO reasoning)."""
from __future__ import annotations

from navigation.seo_intelligence.models import SeoAuditRequest, SeoCapabilityRoute
from navigation.seo_intelligence.planning.capabilities import CAPABILITY_CATALOG
from navigation.seo_intelligence.planning.modes import (
	capabilities_for_mode,
	provider_allowed,
	resolve_effective_mode,
)
from navigation.seo_intelligence.providers.librecrawl.client import base_url as librecrawl_base_url
from navigation.seo_intelligence.registry import SeoProviderRegistry

_CONNECTED = frozenset({'connected', 'degraded'})


class SeoAuditPlanner:
	def __init__(self, registry: SeoProviderRegistry | None = None) -> None:
		self._registry = registry or SeoProviderRegistry()

	def resolve_capabilities(self, request: SeoAuditRequest) -> list[str]:
		mode = resolve_effective_mode(request)
		return capabilities_for_mode(request, mode)

	def _provider_usable(
		self,
		provider_id: str,
		*,
		connections: dict[str, str],
		request: SeoAuditRequest,
	) -> tuple[bool, str]:
		mode = resolve_effective_mode(request)
		if not provider_allowed(provider_id, mode):
			return False, f'{provider_id}_excluded_in_{mode.value}_mode'

		if self._registry.get(provider_id) is None:
			return False, 'provider_unknown'

		status = connections.get(provider_id, 'not_configured')
		if status in _CONNECTED:
			return True, f'{provider_id}_connected'
		if provider_id == 'lighthouse':
			return True, 'lighthouse_always_available'
		if provider_id == 'browser' and request.scan_id:
			return True, 'browser_scan_available'
		if provider_id == 'librecrawl':
			if librecrawl_base_url() and status in _CONNECTED:
				return True, 'librecrawl_connected'
			if librecrawl_base_url():
				return False, 'librecrawl_degraded'
			return False, 'librecrawl_not_configured'
		return False, f'{provider_id}_not_connected'

	def route_capability(
		self,
		capability_id: str,
		request: SeoAuditRequest,
		connections: dict[str, str],
	) -> SeoCapabilityRoute | None:
		spec = CAPABILITY_CATALOG.get(capability_id)
		if spec is None:
			return None
		candidates = [spec.primary_provider, *spec.fallback_providers]
		skipped: list[str] = []

		chosen = ''
		reason = spec.final_fallback

		for pid in candidates:
			usable, pick_reason = self._provider_usable(pid, connections=connections, request=request)
			if usable:
				chosen = pid
				reason = pick_reason
				break
			skipped.append(f'{pid}:{pick_reason}')

		return SeoCapabilityRoute(
			capability_id=capability_id,
			chosen_provider=chosen,
			skipped_providers=skipped,
			reason=reason,
		)

	def build_plan(
		self,
		request: SeoAuditRequest,
		connections: dict[str, str],
	) -> tuple[list[SeoCapabilityRoute], list[str]]:
		"""Return capability routes and provider ids to query."""
		capabilities = self.resolve_capabilities(request)
		routes: list[SeoCapabilityRoute] = []
		provider_order: list[str] = []
		seen: set[str] = set()

		for cap_id in capabilities:
			route = self.route_capability(cap_id, request, connections)
			if route is None:
				continue
			routes.append(route)
			if route.chosen_provider and route.chosen_provider not in seen:
				seen.add(route.chosen_provider)
				provider_order.append(route.chosen_provider)

		return routes, provider_order

	def resolve_provider_ids(self, request: SeoAuditRequest) -> list[str]:
		"""Legacy entry — uses empty connections (pre-collection). Prefer build_plan after status probe."""
		if request.providers:
			mode = resolve_effective_mode(request)
			return [
				pid for pid in request.providers
				if self._registry.get(pid) is not None and provider_allowed(pid, mode)
			]
		_, provider_order = self.build_plan(request, {})
		return provider_order
