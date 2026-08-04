"""AI Visibility Intelligence — derived analysis over collected SEO evidence.

This layer extends SEO Intelligence with AI readiness signals grounded in
Google's public AI search guidance. It does not collect new data or fork the
provider pipeline. See docs/ANALYZER_SOURCES.md.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.adapter import AiVisibilityAdapter
from navigation.seo_intelligence.ai_visibility.analysis import detect_ai_readiness
from navigation.seo_intelligence.ai_visibility.enrich import attach_ai_readiness_block

__all__ = [
	'AiVisibilityAdapter',
	'attach_ai_readiness_block',
	'detect_ai_readiness',
]
