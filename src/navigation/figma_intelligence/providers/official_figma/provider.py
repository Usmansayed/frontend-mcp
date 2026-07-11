"""Official Figma MCP provider — scaffold.

Remote endpoint: https://mcp.figma.com/mcp
See https://developers.figma.com/docs/figma-mcp-server/
"""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.models import (
	CommunitySearchPlan,
	FigmaCandidate,
	FigmaExtractionResult,
	FigmaIntent,
	FigmaSearchPlan,
)


class OfficialFigmaProvider:
	"""Adapter for Figma's official MCP server."""

	provider_id = 'official_figma'
	display_name = 'Figma Official MCP'
	capabilities = frozenset({
		'read_file',
		'read_variables',
		'code_connect',
		'screenshots',
		'use_figma_write',
	})

	async def discover_candidates(
		self,
		plan: FigmaSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: FigmaIntent,
		max_results: int = 20,
	) -> tuple[list[FigmaCandidate], list[str]]:
		_ = plan, community_plan, intent, max_results
		return [], ['official_figma_discovery_not_supported_use_community_adapter']

	async def extract_design(
		self,
		candidate: FigmaCandidate,
		*,
		intent: FigmaIntent,
	) -> FigmaExtractionResult:
		_ = intent
		return FigmaExtractionResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			degraded=['official_figma_extract_not_implemented'],
		)

	async def health(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'status': 'scaffold',
			'endpoint': 'https://mcp.figma.com/mcp',
		}
