"""SEO audit planner — capability-aware, cost-conscious provider routing."""
from __future__ import annotations

import os

from navigation.seo_intelligence.models import SeoAuditRequest, SeoCapabilityRoute
from navigation.seo_intelligence.planning.capabilities import (
	CAPABILITY_CATALOG,
	DEFAULT_AUDIT_CAPABILITIES,
	OPENSEO_BLOCKED_CAPABILITIES,
)
from navigation.seo_intelligence.registry import SeoProviderRegistry

_CONNECTED = frozenset({'connected', 'degraded'})


class SeoAuditPlanner:
	def __init__(self, registry: SeoProviderRegistry | None = None) -> None:
		self._registry = registry or SeoProviderRegistry()

	def resolve_capabilities(self, request: SeoAuditRequest) -> list[str]:
		if request.intents:
			return [c for c in request.intents if c in CAPABILITY_CATALOG]
		return list(DEFAULT_AUDIT_CAPABILITIES)

	def _openseo_configured(self) -> bool:
		return bool(
			os.environ.get('OPENSEO_BASE_URL', '').strip()
			or os.environ.get('OPENSEO_MCP_URL', '').strip()
		)

	def _provider_usable(
		self,
		provider_id: str,
		*,
		connections: dict[str, str],
		request: SeoAuditRequest,
		capability_id: str,
		spec_paid: bool,
	) -> tuple[bool, str]:
		if provider_id == 'openseo':
			if capability_id in OPENSEO_BLOCKED_CAPABILITIES:
				return False, 'openseo_blocked_for_capability'
			if not request.allow_openseo:
				return False, 'openseo_disabled_by_request'
			if not self._openseo_configured():
				return False, 'openseo_not_configured'
			if spec_paid and not request.allow_paid_providers:
				return False, 'paid_provider_blocked'
			status = connections.get('openseo', 'not_configured')
			if status == 'error':
				return False, 'openseo_connection_error'
			return True, 'openseo_available'

		if self._registry.get(provider_id) is None:
			return False, 'provider_unknown'

		status = connections.get(provider_id, 'not_configured')
		if status in _CONNECTED:
			return True, f'{provider_id}_connected'
		if provider_id == 'lighthouse':
			return True, 'lighthouse_always_available'
		if provider_id == 'browser' and request.scan_id:
			return True, 'browser_scan_available'
		if provider_id == 'librecrawl' and os.environ.get('LIBRECRAWL_BASE_URL', '').strip():
			return True, 'librecrawl_configured'
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
		paid = spec.requires_paid_plan or spec.openseo_requires_paid

		for pid in candidates:
			if pid == 'openseo' and capability_id in OPENSEO_BLOCKED_CAPABILITIES:
				skipped.append(f'{pid}:blocked_capability')
				continue
			usable, reason = self._provider_usable(
				pid,
				connections=connections,
				request=request,
				capability_id=capability_id,
				spec_paid=paid and pid == 'openseo',
			)
			if usable:
				return SeoCapabilityRoute(
					capability_id=capability_id,
					chosen_provider=pid,
					skipped_providers=skipped,
					reason=reason,
					paid_provider_used=pid == 'openseo' and (paid or spec.openseo_requires_paid),
				)
			skipped.append(f'{pid}:{reason}')

		return SeoCapabilityRoute(
			capability_id=capability_id,
			chosen_provider='',
			skipped_providers=skipped,
			reason=spec.final_fallback,
			paid_provider_used=False,
		)

	def build_plan(
		self,
		request: SeoAuditRequest,
		connections: dict[str, str],
	) -> tuple[list[SeoCapabilityRoute], list[str]]:
		"""Return capability routes + provider ids to query (deduped, ordered)."""
		capabilities = self.resolve_capabilities(request)
		routes: list[SeoCapabilityRoute] = []
		provider_order: list[str] = []
		seen: set[str] = set()
		degraded: list[str] = []

		for cap_id in capabilities:
			route = self.route_capability(cap_id, request, connections)
			if route is None:
				degraded.append(f'unknown_capability:{cap_id}')
				continue
			routes.append(route)
			if not route.chosen_provider:
				degraded.append(f'capability_unresolved:{cap_id}:{route.reason}')
				continue
			if route.chosen_provider not in seen:
				seen.add(route.chosen_provider)
				provider_order.append(route.chosen_provider)

		return routes, provider_order

	def resolve_provider_ids(self, request: SeoAuditRequest) -> list[str]:
		"""Legacy entry — uses empty connections (pre-collection). Prefer build_plan after status probe."""
		if request.providers:
			return [pid for pid in request.providers if self._registry.get(pid) is not None]
		_, provider_order = self.build_plan(request, {})
		return provider_order
