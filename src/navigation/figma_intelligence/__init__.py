"""Figma Intelligence — user's Figma account, files, and design systems (future).

Public design inspiration lives in ``inspiration_intelligence`` — not here.
This module retains Community duplication, Figma Console providers, and
project-specific extraction until the account-focused API ships.
"""
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
	'FigmaDiscoveryRequest',
	'FigmaDiscoveryResult',
	'FigmaExtractionResult',
	'FigmaIntent',
	'FigmaIntelligenceService',
]
