"""Context7 knowledge source — framework documentation conventions."""
from __future__ import annotations

from navigation.consistency_intelligence.discovery.collect_helpers import build_standard
from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import StandardNode


class Context7KnowledgeSource:
	source_id = 'context7'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		raw = ctx.options.get('context7') or ctx.options.get('context7_conventions')
		if not raw:
			return KnowledgeFragment(source_id=self.source_id, degraded=['context7_no_data_in_context'])

		standards: list[StandardNode] = []
		items = raw if isinstance(raw, list) else raw.get('conventions', []) if isinstance(raw, dict) else []
		for item in items:
			if not isinstance(item, dict):
				continue
			context = str(item.get('context', 'framework'))
			prop = str(item.get('property', ''))
			values = item.get('expected_values') or item.get('values') or []
			if prop and values:
				std = build_standard(
					context=context,
					property_name=prop,
					values=values,
					category='framework',
					provenance='declared',
				)
				if std:
					std.confidence = float(item.get('confidence', 0.85))
					standards.append(std)

		return KnowledgeFragment(
			source_id=self.source_id,
			standards=standards,
			confidence=0.85 if standards else 0.0,
			evidence=[{'kind': 'context7', 'standards_count': len(standards)}],
		)
