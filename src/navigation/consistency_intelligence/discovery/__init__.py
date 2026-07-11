"""Discovery — ingest knowledge from multiple sources into the Project Design Graph."""
from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.merge import MergeStats, merge_fragments
from navigation.consistency_intelligence.discovery.pipeline import DiscoveryPipeline
from navigation.consistency_intelligence.discovery.sources.protocol import (
	KnowledgeFragment,
	KnowledgeSource,
)

__all__ = [
	'DiscoveryContext',
	'DiscoveryPipeline',
	'KnowledgeFragment',
	'KnowledgeSource',
	'MergeStats',
	'merge_fragments',
]
