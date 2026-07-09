"""Framework Intelligence — detect project stack and fetch normalized framework docs."""
from __future__ import annotations

from .models import DocumentationResult, FrameworkKnowledgeResponse, ProjectMetadata
from .providers.documentation import DocumentationProvider, DocumentationProviderError
from .service import FrameworkIntelligenceService

__all__ = [
	'DocumentationProvider',
	'DocumentationProviderError',
	'DocumentationResult',
	'FrameworkIntelligenceService',
	'FrameworkKnowledgeResponse',
	'ProjectMetadata',
]
