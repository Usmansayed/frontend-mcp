"""Community Duplication Pipeline — separate from Community Discovery."""
from navigation.figma_intelligence.community_duplication.models import (
	DuplicationPipelineResult,
	DuplicationRequest,
	DuplicationResult,
)
from navigation.figma_intelligence.community_duplication.orchestrator import (
	CommunityDuplicationOrchestrator,
)

__all__ = [
	'CommunityDuplicationOrchestrator',
	'DuplicationPipelineResult',
	'DuplicationRequest',
	'DuplicationResult',
]
