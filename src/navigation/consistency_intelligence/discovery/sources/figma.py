"""Figma knowledge source — tokens/frames via Design Workflow options."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import TokenNode


class FigmaKnowledgeSource:
	source_id = 'figma'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		raw = ctx.options.get('figma_tokens') or ctx.options.get('figma')
		if not raw:
			return KnowledgeFragment(source_id=self.source_id, degraded=['figma_no_data_in_context'])

		tokens = _tokens_from_payload(raw, source='figma')
		return KnowledgeFragment(
			source_id=self.source_id,
			tokens=tokens,
			confidence=1.0 if tokens else 0.0,
			evidence=[{'kind': 'figma', 'token_count': len(tokens)}],
		)


def _tokens_from_payload(raw: Any, *, source: str) -> list[TokenNode]:
	tokens: list[TokenNode] = []
	items = raw if isinstance(raw, list) else raw.get('tokens', []) if isinstance(raw, dict) else []
	for item in items:
		if not isinstance(item, dict):
			continue
		path_raw = item.get('path') or item.get('name') or item.get('id') or 'token'
		if isinstance(path_raw, str):
			path = tuple(p for p in path_raw.replace('/', '.').split('.') if p)
		else:
			path = tuple(str(p) for p in path_raw)
		value = item.get('value') or item.get('$value')
		tokens.append(
			TokenNode(
				path=path,
				dtcg_type=item.get('type') or item.get('$type'),
				value=value,
				resolved_value=item.get('resolved_value') or value,
				layer=str(item.get('layer', 'semantic')),
				source=source,
				provenance='declared',
				confidence=1.0,
			)
		)
	return tokens
