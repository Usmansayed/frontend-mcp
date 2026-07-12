"""Figma Intelligence — connection + coordination for user's Figma workspace.

Orchestrates southleft/figma-console-mcp. Public inspiration lives in
``inspiration_intelligence`` — not here.
"""
from navigation.figma_intelligence.context_models import FigmaDesignContext
from navigation.figma_intelligence.models import (
	FigmaCandidate,
	FigmaDiscoveryRequest,
	FigmaDiscoveryResult,
	FigmaExtractionResult,
	FigmaIntent,
)
from navigation.figma_intelligence.service import FigmaIntelligenceService

__all__ = [
	'FigmaCandidate',
	'FigmaDesignContext',
	'FigmaDiscoveryRequest',
	'FigmaDiscoveryResult',
	'FigmaExtractionResult',
	'FigmaIntent',
	'FigmaIntelligenceService',
]
