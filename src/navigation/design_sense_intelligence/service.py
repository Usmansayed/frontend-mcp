"""Design sense intelligence service facade."""
from __future__ import annotations

from navigation.design_sense_intelligence.heuristics.visual_insights import collect_visual_insights
from navigation.design_sense_intelligence.heuristics.quality_hints import build_suggested_fixes


class DesignSenseService:
	"""Facade for layout heuristics, UX validation, and design hints."""

	collect_visual_insights = staticmethod(collect_visual_insights)
	build_suggested_fixes = staticmethod(build_suggested_fixes)
