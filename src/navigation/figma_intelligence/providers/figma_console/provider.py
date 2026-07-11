"""Figma Console MCP — extraction-only execution provider (PAT)."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.models import (
	CommunitySearchPlan,
	FigmaCandidate,
	FigmaExtractionResult,
	FigmaIntent,
	FigmaSearchPlan,
)
from navigation.figma_intelligence.providers.figma_console.client import FigmaConsoleMcpClient
from navigation.figma_intelligence.providers.figma_console.extract import normalize_kit_payload


class FigmaConsoleProvider:
	"""southleft/figma-console-mcp — deep extraction only. Never discovers Community templates."""

	provider_id = 'figma_console'
	display_name = 'Figma Console MCP'
	capabilities = frozenset({
		'read_file',
		'read_variables',
		'read_components',
		'design_system_kit',
		'screenshots',
		'token_export',
		'auto_layout',
		'styles',
	})

	def __init__(self, *, client: FigmaConsoleMcpClient | None = None) -> None:
		self._client = client or FigmaConsoleMcpClient()

	async def discover_candidates(
		self,
		plan: FigmaSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: FigmaIntent,
		max_results: int = 20,
	) -> tuple[list[FigmaCandidate], list[str]]:
		_ = plan, community_plan, intent, max_results
		return [], ['figma_console_discovery_not_supported_use_community_adapter']

	async def extract_design(
		self,
		candidate: FigmaCandidate,
		*,
		intent: FigmaIntent,
	) -> FigmaExtractionResult:
		_ = intent
		if not candidate.file_key:
			return FigmaExtractionResult(
				candidate_id=candidate.candidate_id,
				provider_id=self.provider_id,
				degraded=['figma_console_missing_file_key'],
			)

		payload, degraded = await self._client.call_tool(
			'figma_get_design_system_kit',
			{'fileKey': candidate.file_key},
		)
		if payload is None:
			payload, more = await self._client.call_tool(
				'figma_get_file_data',
				{'fileKey': candidate.file_key},
			)
			degraded.extend(more)

		return normalize_kit_payload(candidate, payload if isinstance(payload, dict) else None, degraded=degraded)

	async def health(self) -> dict[str, Any]:
		if not self._client.available():
			return {
				'provider_id': self.provider_id,
				'status': 'unavailable',
				'mcp': 'southleft/figma-console-mcp',
				'note': 'FIGMA_ACCESS_TOKEN required for extraction (not discovery)',
			}
		return await self._client.health()
