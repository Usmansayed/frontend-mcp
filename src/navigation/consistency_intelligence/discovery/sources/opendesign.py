"""Open Design / UX Magic knowledge source."""
from __future__ import annotations

from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.figma import _tokens_from_payload
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import PatternNode


class OpenDesignKnowledgeSource:
	source_id = 'opendesign'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		raw = ctx.options.get('opendesign') or ctx.options.get('opendesign_tokens')
		if not raw:
			return KnowledgeFragment(source_id=self.source_id, degraded=['opendesign_no_data_in_context'])

		tokens = _tokens_from_payload(raw, source='opendesign')
		patterns: dict[str, PatternNode] = {}
		if isinstance(raw, dict):
			for pname in raw.get('patterns') or []:
				name = str(pname)
				patterns[name.lower()] = PatternNode(
					name=name,
					description='From Open Design project',
					confidence=0.9,
					support_count=1,
				)

		return KnowledgeFragment(
			source_id=self.source_id,
			tokens=tokens,
			patterns=patterns,
			confidence=1.0 if tokens or patterns else 0.0,
			evidence=[{'kind': 'opendesign', 'token_count': len(tokens), 'pattern_count': len(patterns)}],
		)
