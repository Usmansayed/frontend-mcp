"""Knowledge source protocol — sources emit fragments, never write the graph directly."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	ExceptionNode,
	PatternNode,
	RelationshipEdge,
	StandardNode,
	TokenNode,
)

from ..context import DiscoveryContext


@dataclass(slots=True)
class KnowledgeFragment:
	"""Evidence bundle from one knowledge source before pipeline merge."""

	source_id: str
	standards: list[StandardNode] = field(default_factory=list)
	tokens: list[TokenNode] = field(default_factory=list)
	components: dict[str, ComponentNode] = field(default_factory=dict)
	patterns: dict[str, PatternNode] = field(default_factory=dict)
	relationships: list[RelationshipEdge] = field(default_factory=list)
	exceptions: list[ExceptionNode] = field(default_factory=list)
	evidence: list[dict[str, Any]] = field(default_factory=list)
	confidence: float = 0.0
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'source_id': self.source_id,
			'standards_count': len(self.standards),
			'tokens_count': len(self.tokens),
			'components_count': len(self.components),
			'patterns_count': len(self.patterns),
			'relationships_count': len(self.relationships),
			'exceptions_count': len(self.exceptions),
			'confidence': self.confidence,
			'degraded': list(self.degraded),
		}


@runtime_checkable
class KnowledgeSource(Protocol):
	"""Pluggable knowledge producer — Phase 2 implements collect()."""

	source_id: str

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		"""Extract design-language evidence from this source."""
		...
