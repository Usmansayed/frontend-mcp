"""Design token extractor — CSS variables and inferred scales."""
from __future__ import annotations

import re
from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import parse_px

_COLOR_VAR = re.compile(r'color|bg|background|foreground|primary|accent', re.I)
_SPACE_VAR = re.compile(r'space|spacing|gap|padding|margin', re.I)
_RADIUS_VAR = re.compile(r'radius|rounded', re.I)
_TYPE_VAR = re.compile(r'font|text|leading', re.I)


class DesignTokenExtractor:
	name = 'design_tokens'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		vars_map = dict(context.css_variables)
		color_tokens: dict[str, str] = {}
		spacing_vals: list[int] = []
		radius_vals: list[int] = []
		type_vals: list[int] = []
		issues: list[dict[str, Any]] = []

		for name, value in vars_map.items():
			if _COLOR_VAR.search(name):
				color_tokens[name] = value
			if _SPACE_VAR.search(name):
				px = parse_px(value)
				if px is not None:
					spacing_vals.append(int(round(px)))
			if _RADIUS_VAR.search(name):
				px = parse_px(value)
				if px is not None:
					radius_vals.append(int(round(px)))
			if _TYPE_VAR.search(name):
				px = parse_px(value)
				if px is not None:
					type_vals.append(int(round(px)))

		if not vars_map:
			issues.append({
				'kind': 'no_css_variables',
				'severity': 'advisory',
				'detail': 'No CSS custom properties detected on :root',
			})

		return {
			'design_tokens': {
				'css_variables': vars_map,
				'spacing_scale': sorted(set(spacing_vals))[:16],
				'radius_scale': sorted(set(radius_vals))[:12],
				'typography_scale': sorted(set(type_vals))[:12],
				'color_tokens': color_tokens,
				'source': 'computed_root' if vars_map else 'none',
				'issues': issues,
			},
		}
