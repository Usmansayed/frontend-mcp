"""Registered design extractors."""
from __future__ import annotations

from .accessibility import AccessibilityExtractor
from .color import ColorExtractor
from .components import ComponentExtractor
from .design_tokens import DesignTokenExtractor
from .grid import GridExtractor
from .hierarchy import HierarchyExtractor
from .layout import LayoutExtractor
from .motion import MotionExtractor
from .spacing import SpacingExtractor
from .typography import TypographyExtractor

__all__ = [
	'AccessibilityExtractor',
	'ColorExtractor',
	'ComponentExtractor',
	'DesignTokenExtractor',
	'GridExtractor',
	'HierarchyExtractor',
	'LayoutExtractor',
	'MotionExtractor',
	'SpacingExtractor',
	'TypographyExtractor',
	'default_extractors',
]


def default_extractors():
	return [
		TypographyExtractor(),
		SpacingExtractor(),
		ColorExtractor(),
		LayoutExtractor(),
		GridExtractor(),
		HierarchyExtractor(),
		ComponentExtractor(),
		MotionExtractor(),
		AccessibilityExtractor(),
		DesignTokenExtractor(),
	]
