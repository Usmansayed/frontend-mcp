"""Figma Intelligence service facade — connection + coordination layer."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.community_duplication.models import (
	DuplicationPipelineResult,
	DuplicationRequest,
)
from navigation.figma_intelligence.community_duplication.orchestrator import (
	CommunityDuplicationOrchestrator,
)
from navigation.figma_intelligence.connection.manager import FigmaConnectionManager
from navigation.figma_intelligence.context_models import FigmaDesignContext
from navigation.figma_intelligence.coordination.coordinator import FigmaCoordinationLayer
from navigation.figma_intelligence.health.monitor import FigmaHealthMonitor
from navigation.figma_intelligence.models import FigmaDiscoveryRequest, FigmaDiscoveryResult, FigmaPipelineResult
from navigation.figma_intelligence.planning.orchestrator import FigmaPipelineOrchestrator
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry
from navigation.figma_intelligence.session.manager import FigmaSessionManager


class FigmaIntelligenceService:
	"""Connection + coordination layer for the user's Figma workspace.

	Orchestrates southleft/figma-console-mcp — does not reimplement it.
	Legacy community pipeline APIs remain for backward compatibility.
	"""

	def __init__(
		self,
		providers: FigmaProviderRegistry | None = None,
		*,
		connection: FigmaConnectionManager | None = None,
		session: FigmaSessionManager | None = None,
		coordinator: FigmaCoordinationLayer | None = None,
		health: FigmaHealthMonitor | None = None,
	) -> None:
		self._providers = providers or FigmaProviderRegistry()
		self._connection = connection or FigmaConnectionManager()
		self._session = session or FigmaSessionManager()
		self._coordinator = coordinator or FigmaCoordinationLayer(
			connection=self._connection,
			session=self._session,
		)
		self._health = health or FigmaHealthMonitor(connection=self._connection)
		self._orchestrator = FigmaPipelineOrchestrator(self._providers)
		self._duplication = CommunityDuplicationOrchestrator()

	async def connect(self, pat: str, *, account_hint: str = '') -> dict[str, Any]:
		result = await self._connection.connect(pat, account_hint=account_hint)
		self._coordinator.invalidate_cache()
		return result

	def disconnect(self) -> dict[str, Any]:
		result = self._connection.disconnect()
		self._coordinator.invalidate_cache()
		return result

	async def health(self) -> dict[str, Any]:
		return await self._health.check()

	def connection_status(self) -> dict[str, Any]:
		return self._connection.status()

	async def get_context(self, *, refresh: bool = False) -> FigmaDesignContext:
		return await self._coordinator.get_design_context(refresh=refresh)

	async def list_files(self) -> list[dict[str, str]]:
		return await self._coordinator.list_files()

	def set_active_file(
		self,
		*,
		file_key: str = '',
		file_url: str = '',
		file_name: str = '',
	) -> dict[str, Any]:
		from navigation.figma_intelligence.adapter.console import parse_file_key

		key = file_key.strip() or parse_file_key(file_url)
		state = self._session.set_active_file(file_key=key, file_url=file_url, file_name=file_name)
		self._coordinator.invalidate_cache()
		return state.to_dict()

	def set_active_page(self, page_id: str) -> dict[str, Any]:
		state = self._session.set_active_page(page_id)
		self._coordinator.invalidate_cache()
		return state.to_dict()

	def set_active_frame(self, frame_id: str) -> dict[str, Any]:
		state = self._session.set_active_frame(frame_id)
		self._coordinator.invalidate_cache()
		return state.to_dict()

	def set_selection(self, node_ids: list[str]) -> dict[str, Any]:
		state = self._session.set_selection(node_ids)
		self._coordinator.invalidate_cache()
		return state.to_dict()

	async def discover(self, request: FigmaDiscoveryRequest) -> FigmaDiscoveryResult:
		return await self._orchestrator.discover(request)

	async def run_pipeline(self, request: FigmaDiscoveryRequest) -> FigmaPipelineResult:
		return await self._orchestrator.run_pipeline(request)

	async def run_duplication_pipeline(self, request: DuplicationRequest) -> DuplicationPipelineResult:
		return await self._duplication.run(request)

	def list_providers(self) -> list[dict[str, object]]:
		return self._providers.list_providers()

	def status(self) -> dict[str, object]:
		conn = self.connection_status()
		return {
			'module': 'figma_intelligence',
			'phase': 'connection_coordination_v2',
			'role': 'connection_and_coordination',
			'mcp_backend': 'southleft/figma-console-mcp',
			'connected': conn.get('connected'),
			'token_source': conn.get('token_source'),
			'session': self._session.load().to_dict(),
			'legacy_pipeline': 'available',
			'providers': self.list_providers(),
		}
