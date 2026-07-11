"""Spacing extractor."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style, infer_base_unit, parse_px, parse_sides, unique_sorted

_SCALE = (0, 4, 8, 12, 16, 24, 32, 48, 64)


class SpacingExtractor:
	name = 'spacing'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		padding_vals: list[float] = []
		margin_vals: list[float] = []
		gap_vals: list[float] = []
		matrix: list[dict[str, Any]] = []
		off_scale = 0
		issues: list[dict[str, Any]] = []

		for el in context.elements[:80]:
			style = element_style(el)
			pad = parse_sides(style.get('padding'))
			mar = parse_sides(style.get('margin'))
			gap = parse_px(style.get('gap'))
			padding_vals.extend(pad)
			margin_vals.extend(mar)
			if gap is not None:
				gap_vals.append(gap)

			for label, vals in (('padding', pad), ('margin', mar)):
				for v in vals:
					if v > 0 and round(v) not in _SCALE:
						off_scale += 1
						if len(issues) < 15:
							issues.append({
								'kind': 'off_scale_spacing',
								'severity': 'minor',
								'detail': f'{label} {v}px on {el.get("tag")}',
							})

			if pad or mar or gap is not None:
				matrix.append({
					'tag': el.get('tag'),
					'selector': el.get('selector'),
					'padding_px': pad,
					'margin_px': mar,
					'gap_px': gap,
				})

		all_vals = padding_vals + margin_vals + gap_vals
		base = infer_base_unit([v for v in all_vals if v > 0])

		return {
			'spacing': {
				'padding_values_px': unique_sorted(padding_vals),
				'margin_values_px': unique_sorted(margin_vals),
				'gap_values_px': unique_sorted(gap_vals),
				'base_unit_px': base,
				'off_scale_count': off_scale,
				'matrix': matrix[:40],
				'issues': issues,
			},
		}
