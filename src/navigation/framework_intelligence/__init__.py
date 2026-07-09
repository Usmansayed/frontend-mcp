"""Framework Intelligence — detect project stack and fetch normalized framework docs."""
from __future__ import annotations

from .models import FrameworkKnowledgeResponse, ProjectMetadata
from .service import FrameworkIntelligenceService

__all__ = [
	'FrameworkIntelligenceService',
	'FrameworkKnowledgeResponse',
	'ProjectMetadata',
]
