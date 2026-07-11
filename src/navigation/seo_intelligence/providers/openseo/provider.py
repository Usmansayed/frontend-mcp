"""OpenSEO provider — optional MCP adapter (not a hard dependency)."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoAuditRequest, SeoEvidenceRef, SeoProviderMeta
from navigation.seo_intelligence.providers.openseo.capabilities import (
	OPENSEO_DO_NOT_ROUTE,
	OPENSEO_FREE_CAPABILITIES,
	OPENSEO_PAID_CAPABILITIES,
)
from navigation.seo_intelligence.providers.openseo.client import OpenSeoMcpClient, resolve_mcp_url
from navigation.seo_intelligence.providers.openseo.normalize import (
	normalize_inspect_urls,
	normalize_search_console_performance,
)


class OpenSeoProvider:
	provider_id = 'openseo'

	def __init__(self, client: OpenSeoMcpClient | None = None) -> None:
		self._client = client

	def _mcp(self) -> OpenSeoMcpClient:
		return self._client or OpenSeoMcpClient()

	def provider_meta(self) -> SeoProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def connection_status(self, request: SeoAuditRequest) -> tuple[str, list[str]]:
		degraded: list[str] = []
		if not resolve_mcp_url():
			return 'not_configured', ['openseo_not_configured:set_OPENSEO_BASE_URL_or_OPENSEO_MCP_URL']
		if not request.allow_openseo:
			return 'not_configured', ['openseo_disabled:allow_openseo=false']

		client = self._mcp()
		if not client.project_configured():
			degraded.append('openseo_project_id_missing:set_OPENSEO_PROJECT_ID')

		health = await client.health()
		degraded.extend(health.get('degraded') or [])
		if health.get('status') == 'ok':
			return 'connected', degraded
		if client.configured():
			return 'degraded', degraded
		return 'not_configured', degraded

	async def collect(
		self,
		request: SeoAuditRequest,
		*,
		capabilities: list[str] | None = None,
	) -> tuple[list[SeoEvidenceRef], list[str]]:
		client = self._mcp()
		if not client.configured() or not request.allow_openseo:
			return [], ['openseo_skipped:not_configured_or_disabled']

		requested = set(capabilities or [])
		if not requested:
			return [], ['openseo_no_capabilities_routed']

		blocked = requested & set(OPENSEO_DO_NOT_ROUTE)
		if blocked:
			return [], [f'openseo_blocked_capabilities:{",".join(sorted(blocked))}']

		paid_requested = requested & set(OPENSEO_PAID_CAPABILITIES)
		if paid_requested and not request.allow_paid_providers:
			return [], ['openseo_paid_capabilities_blocked:set_allow_paid_providers=true']

		evidence: list[SeoEvidenceRef] = []
		degraded: list[str] = []

		free_requested = requested & set(OPENSEO_FREE_CAPABILITIES)
		for capability_id in sorted(free_requested):
			cap_evidence, cap_deg = await self._collect_free(client, request, capability_id)
			evidence.extend(cap_evidence)
			degraded.extend(cap_deg)

		if paid_requested:
			if request.allow_paid_providers:
				degraded.append(
					'openseo_paid_adapter_not_implemented:free_capabilities_only;'
					f'blocked={",".join(sorted(paid_requested))}'
				)
			else:
				degraded.append('openseo_paid_capabilities_blocked:set_allow_paid_providers=true')

		if not evidence and not degraded:
			degraded.append('openseo_no_evidence_collected')

		return evidence, degraded

	async def _collect_free(
		self,
		client: OpenSeoMcpClient,
		request: SeoAuditRequest,
		capability_id: str,
	) -> tuple[list[SeoEvidenceRef], list[str]]:
		spec = OPENSEO_FREE_CAPABILITIES.get(capability_id)
		if spec is None:
			return [], [f'openseo_unknown_free_capability:{capability_id}']

		tool_name = str(spec['mcp_tool'])
		if capability_id == 'search_queries':
			payload, call_deg = await client.call_tool(
				tool_name,
				{
					'dimensions': ['query'],
					'dateRange': 'last_28_days',
					'rowLimit': 50,
				},
			)
			if payload is None:
				return [], call_deg
			evidence, norm_deg = normalize_search_console_performance(payload)
			return evidence, call_deg + norm_deg

		if capability_id == 'index_status':
			urls = _inspection_urls(request)
			if not urls:
				return [], ['openseo_inspect_urls:no_urls']
			payload, call_deg = await client.call_tool(tool_name, {'urls': urls})
			if payload is None:
				return [], call_deg
			evidence, norm_deg = normalize_inspect_urls(payload)
			return evidence, call_deg + norm_deg

		return [], [f'openseo_free_capability_unhandled:{capability_id}']


def _inspection_urls(request: SeoAuditRequest) -> list[str]:
	urls: list[str] = []
	if request.website_url.strip():
		urls.append(request.website_url.strip())
	if request.property_url.strip().startswith('http'):
		prop = request.property_url.strip()
		if prop not in urls:
			urls.append(prop)
	return urls[:10]
