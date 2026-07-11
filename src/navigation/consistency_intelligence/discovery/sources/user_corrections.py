"""User corrections knowledge source — agent-approved exceptions and overrides."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import ExceptionNode, StandardNode


class UserCorrectionsKnowledgeSource:
	source_id = 'user_corrections'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		raw = ctx.options.get('user_corrections') or ctx.options.get('exceptions') or []
		if not raw:
			return KnowledgeFragment(
				source_id=self.source_id,
				degraded=['user_corrections_none_provided'],
			)

		exceptions: list[ExceptionNode] = []
		standards: list[StandardNode] = []
		for item in raw:
			if not isinstance(item, dict):
				continue
			if item.get('standard_id'):
				exceptions.append(
					ExceptionNode(
						standard_id=str(item['standard_id']),
						element_pattern=str(item.get('element_pattern', '')),
						actual_value=str(item.get('actual_value', '')),
						rationale=str(item.get('rationale', '')),
						approved_by=item.get('approved_by'),
					)
				)
			if item.get('id') and item.get('property'):
				standards.append(
					StandardNode(
						id=str(item['id']),
						category=str(item.get('category', 'user')),
						context=str(item.get('context', '')),
						property=str(item['property']),
						expected_values=list(item.get('expected_values') or []),
						confidence=float(item.get('confidence', 1.0)),
						support_count=int(item.get('support_count', 1)),
						provenance='user',
					)
				)

		return KnowledgeFragment(
			source_id=self.source_id,
			standards=standards,
			exceptions=exceptions,
			confidence=1.0 if exceptions or standards else 0.0,
			evidence=[{'kind': 'user_corrections', 'count': len(exceptions) + len(standards)}],
		)
