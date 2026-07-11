"""Typography extractor."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style, parse_px, unique_sorted

_ALLOWED_SIZES = {12, 14, 16, 18, 20, 24, 30, 36}


class TypographyExtractor:
	name = 'typography'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		families: set[str] = set()
		sizes: list[float] = []
		line_heights: list[float] = []
		headings: list[dict[str, Any]] = []
		body_samples: list[dict[str, Any]] = []
		issues: list[dict[str, Any]] = []

		for el in context.elements:
			style = element_style(el)
			tag = str(el.get('tag') or '')
			fam = style.get('fontFamily')
			if fam:
				families.add(str(fam).split(',')[0].strip().strip('"'))
			fs = parse_px(style.get('fontSize'))
			if fs is not None:
				sizes.append(fs)
				if fs not in _ALLOWED_SIZES and not any(
					c in (el.get('classes') or []) for c in ('text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl')
				):
					issues.append({
						'kind': 'off_scale_font_size',
						'severity': 'minor',
						'detail': f'{tag} font-size {fs}px',
						'selector': el.get('selector'),
					})
			lh = parse_px(style.get('lineHeight'))
			if lh is not None:
				line_heights.append(lh)

			if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
				headings.append({
					'level': int(tag[1]),
					'text': el.get('text', '')[:60],
					'font_size_px': fs,
					'font_family': fam,
				})
			elif tag in ('p', 'span', 'label') and len(body_samples) < 8:
				body_samples.append({
					'tag': tag,
					'font_size_px': fs,
					'line_height_px': lh,
					'text': el.get('text', '')[:40],
				})

		return {
			'typography': {
				'font_families': sorted(families)[:12],
				'font_sizes_px': unique_sorted(sizes),
				'line_heights': unique_sorted(line_heights),
				'heading_levels': headings,
				'body_samples': body_samples,
				'scale_on_grid': all(s in _ALLOWED_SIZES for s in sizes) if sizes else False,
				'issues': issues[:20],
				'element_count': len(context.elements),
			},
		}
