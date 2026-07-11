"""Placeholder for future knowledge sources — git history, design docs, user corrections."""
from __future__ import annotations

from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment


class FutureKnowledgeSource:
	"""Stub for sources not yet implemented (git_history, design_docs, user_corrections)."""

	source_id = 'future'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		_ = ctx
		return KnowledgeFragment(
			source_id=self.source_id,
			degraded=['future_source_not_enabled'],
		)
