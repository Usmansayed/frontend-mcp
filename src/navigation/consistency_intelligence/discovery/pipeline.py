"""Discovery pipeline — merge knowledge fragments into Project Design Graph."""
from __future__ import annotations

import asyncio

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph

from .context import DiscoveryContext
from .merge import MergeStats, merge_fragments
from .sources.protocol import KnowledgeFragment, KnowledgeSource


class DiscoveryPipeline:
	"""Run knowledge sources and merge fragments into the graph."""

	def __init__(self, sources: list[KnowledgeSource] | None = None) -> None:
		self._sources = list(sources or [])

	@property
	def sources(self) -> list[KnowledgeSource]:
		return list(self._sources)

	async def run(
		self,
		ctx: DiscoveryContext,
		graph: ProjectDesignGraph,
	) -> tuple[ProjectDesignGraph, list[str], MergeStats]:
		"""Execute enabled sources and merge into graph."""
		degraded: list[str] = []
		if not self._sources:
			degraded.append('no_sources_registered')
			return graph, degraded, MergeStats()

		enabled = [
			s for s in self._sources
			if not ctx.enabled_sources or s.source_id in ctx.enabled_sources
		]
		if not enabled:
			degraded.append('no_enabled_sources')
			return graph, degraded, MergeStats()

		fragments = await asyncio.gather(*[s.collect(ctx) for s in enabled])
		for fragment in fragments:
			degraded.extend(fragment.degraded)

		non_empty = [f for f in fragments if _fragment_has_payload(f)]
		if not non_empty:
			degraded.append('all_sources_empty')
			return graph, degraded, MergeStats()

		graph, stats = merge_fragments(graph, non_empty)
		return graph, degraded, stats


def _fragment_has_payload(fragment: KnowledgeFragment) -> bool:
	return bool(
		fragment.standards
		or fragment.tokens
		or fragment.components
		or fragment.patterns
		or fragment.relationships
		or fragment.exceptions
	)
