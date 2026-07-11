"""Figma Intelligence service facade."""
from __future__ import annotations

from navigation.figma_intelligence.community_duplication.models import (
	DuplicationPipelineResult,
	DuplicationRequest,
)
from navigation.figma_intelligence.community_duplication.orchestrator import (
	CommunityDuplicationOrchestrator,
)
from navigation.figma_intelligence.models import FigmaDiscoveryRequest, FigmaDiscoveryResult, FigmaPipelineResult
from navigation.figma_intelligence.planning.orchestrator import FigmaPipelineOrchestrator
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry


class FigmaIntelligenceService:
	"""Orchestration layer — our MCP remains the brain.

	Figma Console / Official Figma MCP are execution providers only.
	"""

	def __init__(self, providers: FigmaProviderRegistry | None = None) -> None:
		self._providers = providers or FigmaProviderRegistry()
		self._orchestrator = FigmaPipelineOrchestrator(self._providers)
		self._duplication = CommunityDuplicationOrchestrator()

	async def discover(self, request: FigmaDiscoveryRequest) -> FigmaDiscoveryResult:
		return await self._orchestrator.discover(request)

	async def run_pipeline(self, request: FigmaDiscoveryRequest) -> FigmaPipelineResult:
		return await self._orchestrator.run_pipeline(request)

	async def run_duplication_pipeline(self, request: DuplicationRequest) -> DuplicationPipelineResult:
		"""Community template → Drafts file_key → official REST → Design Snapshot."""
		return await self._duplication.run(request)

	def list_providers(self) -> list[dict[str, object]]:
		return self._providers.list_providers()

	def status(self) -> dict[str, object]:
		return {
			'module': 'figma_intelligence',
			'phase': 'architecture_frozen_v1',
			'providers': self.list_providers(),
		}
