"""Color extractor."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import contrast_ratio, element_style, is_css_var

_MIN_CONTRAST = 4.5


class ColorExtractor:
	name = 'colors'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		palette: dict[str, dict[str, Any]] = {}
		text_colors: set[str] = set()
		bg_colors: set[str] = set()
		accent_colors: set[str] = set()
		contrast_pairs: list[dict[str, Any]] = []
		wcag_failures: list[dict[str, Any]] = []
		raw_count = 0
		token_backed = 0
		issues: list[dict[str, Any]] = []

		for el in context.elements:
			style = element_style(el)
			tag = str(el.get('tag') or '')
			fg = style.get('color')
			bg = style.get('backgroundColor')
			for prop, val in (('color', fg), ('backgroundColor', bg)):
				if not val or val in ('rgba(0, 0, 0, 0)', 'transparent'):
					continue
				if is_css_var(val):
					token_backed += 1
				elif val.startswith('rgb') or val.startswith('#'):
					raw_count += 1
					if len(issues) < 10:
						issues.append({
							'kind': 'raw_color',
							'severity': 'minor',
							'detail': f'{prop}={val} on {tag}',
						})
				key = str(val)
				if key not in palette:
					palette[key] = {'value': key, 'count': 0, 'roles': []}
				palette[key]['count'] += 1
				palette[key]['roles'].append(tag)

			if fg:
				text_colors.add(str(fg))
			if bg and bg not in ('rgba(0, 0, 0, 0)', 'transparent'):
				bg_colors.add(str(bg))
			if tag in ('button', 'a') and fg:
				accent_colors.add(str(fg))

			if fg and bg and str(bg) not in ('rgba(0, 0, 0, 0)', 'transparent'):
				ratio = contrast_ratio(str(fg), str(bg))
				if ratio is not None:
					pair = {'foreground': fg, 'background': bg, 'ratio': round(ratio, 2), 'tag': tag}
					contrast_pairs.append(pair)
					if ratio < _MIN_CONTRAST and len(wcag_failures) < 20:
						wcag_failures.append({**pair, 'required': _MIN_CONTRAST})

		total = raw_count + token_backed
		matrix = [
			{
				'foreground': p['foreground'],
				'background': p['background'],
				'ratio': p['ratio'],
				'wcag_aa': p['ratio'] >= _MIN_CONTRAST,
				'tag': p.get('tag'),
			}
			for p in contrast_pairs
		]
		return {
			'colors': {
				'palette': sorted(palette.values(), key=lambda p: -p['count'])[:24],
				'text_colors': sorted(text_colors)[:16],
				'background_colors': sorted(bg_colors)[:16],
				'accent_colors': sorted(accent_colors)[:8],
				'contrast_pairs': contrast_pairs[:30],
				'contrast_matrix': matrix[:30],
				'wcag_failures': wcag_failures,
				'raw_color_count': raw_count,
				'token_backed_ratio': round(token_backed / total, 3) if total else 0.0,
				'issues': issues,
			},
		}
