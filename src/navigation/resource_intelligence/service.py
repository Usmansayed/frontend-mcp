"""Resource Intelligence service facade."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from navigation.resource_intelligence.graph.store import ResourceGraphStore
from navigation.resource_intelligence.license.resolver import build_license_summary
from navigation.resource_intelligence.models import ResourceDiscoveryRequest, ResourceRecommendation
from navigation.resource_intelligence.planning.orchestrator import ResourceSearchOrchestrator
from navigation.resource_intelligence.registry import ResourceProviderRegistry
from navigation.resource_intelligence.tools.blob_store import ResourceBlobStore


class ResourceIntelligenceService:
	"""Orchestration layer for multi-provider creative assets."""

	def __init__(
		self,
		providers: ResourceProviderRegistry | None = None,
		*,
		orchestrator: ResourceSearchOrchestrator | None = None,
		graph: ResourceGraphStore | None = None,
	) -> None:
		self._providers = providers or ResourceProviderRegistry()
		self._orchestrator = orchestrator or ResourceSearchOrchestrator(registry=self._providers, graph=graph)
		self._graph = graph or ResourceGraphStore()
		self._blob_store = ResourceBlobStore()

	def list_providers(
		self,
		*,
		commercial_only: bool = True,
		include_non_commercial: bool = False,
	) -> list[dict[str, object]]:
		return self._providers.list_providers(
			commercial_only=commercial_only,
			include_non_commercial=include_non_commercial,
		)

	def list_excluded_providers(self) -> list[dict[str, object]]:
		return self._providers.list_excluded()

	def graph_summary(self) -> dict[str, object]:
		return self._graph.summary()

	async def search(self, request: ResourceDiscoveryRequest) -> ResourceRecommendation:
		return await self._orchestrator.search(request)

	async def resolve_from_observe(
		self,
		*,
		scan_id: str,
		query: str,
		scans: Any,
		repo_root: str = '',
		icon_family: str | None = None,
	) -> dict[str, Any]:
		from navigation.resource_intelligence.observe_bridge import resolve_from_observe

		return await resolve_from_observe(
			scan_id=scan_id,
			query=query,
			scans=scans,
			repo_root=repo_root,
			icon_family=icon_family,
		)

	def check_license(self, asset_dict: dict[str, Any], request: ResourceDiscoveryRequest) -> dict[str, Any]:
		from navigation.resource_intelligence.models import LicenseProfile

		lic = asset_dict.get('license') or {}
		profile = LicenseProfile(
			spdx_id=str(lic.get('spdx_id') or 'UNKNOWN'),
			commercial_use=bool(lic.get('commercial_use')),
			attribution_required=bool(lic.get('attribution_required')),
			redistribution_allowed=bool(lic.get('redistribution_allowed', True)),
			mcp_download_allowed=bool(lic.get('mcp_download_allowed', True)),
			ai_training_allowed=bool(lic.get('ai_training_allowed', True)),
			dataset_use_allowed=bool(lic.get('dataset_use_allowed', True)),
			api_automation_allowed=bool(lic.get('api_automation_allowed', True)),
			self_hostable=bool(lic.get('self_hostable')),
			notes=list(lic.get('notes') or []),
			source_url=str(lic.get('source_url') or ''),
		)
		return build_license_summary(profile, request, provider_id=str(asset_dict.get('provider_id') or '')).to_dict()

	def status(self) -> dict[str, object]:
		from navigation.resource_intelligence.providers.manager import ResourceProviderManager

		live = ResourceProviderManager().list_live_providers()
		return {
			'module': 'resource_intelligence',
			'phase': 'production_v2',
			'providers_commercial': len(self.list_providers(commercial_only=True)),
			'providers_excluded': len(self.list_excluded_providers()),
			'providers_live': live,
			'commercial_only_default': True,
			'blob_ttl_hours': float(os.environ.get('RESOURCE_BLOB_TTL_HOURS', '24')),
			'graph': self._graph.summary(),
		}

	def end_resource_session(self, session_id: str) -> dict[str, Any]:
		removed = self._blob_store.end_session(session_id)
		return {'session_id': session_id, 'removed': removed}

	def cleanup_resource_blobs(self) -> dict[str, Any]:
		removed = self._blob_store.cleanup_expired()
		return {'expired_sessions_removed': removed}
