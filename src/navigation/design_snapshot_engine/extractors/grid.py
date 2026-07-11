"""Grid extractor."""
from __future__ import annotations

import re
from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style, parse_px


class GridExtractor:
	name = 'grid'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		grids: list[dict[str, Any]] = []
		column_counts: list[int] = []
		gutters: list[float] = []
		issues: list[dict[str, Any]] = []

		for el in context.elements:
			style = element_style(el)
			display = style.get('display', '')
			cols = style.get('gridTemplateColumns', '')
			if display == 'grid' or (cols and cols != 'none'):
				col_count = len([c for c in str(cols).split() if c.strip() and c != 'none'])
				if col_count:
					column_counts.append(col_count)
				cg = parse_px(style.get('columnGap'))
				rg = parse_px(style.get('rowGap'))
				if cg is not None:
					gutters.append(cg)
				if rg is not None:
					gutters.append(rg)
				grids.append({
					'tag': el.get('tag'),
					'columns': cols,
					'column_gap_px': cg,
					'row_gap_px': rg,
					'classes': el.get('classes', [])[:4],
				})

			classes = el.get('classes') or []
			if any('grid' in c or 'cols-' in c for c in classes):
				m = re.search(r'cols-(\d+)', ' '.join(classes))
				if m:
					column_counts.append(int(m.group(1)))

		alignment = 1.0 if grids else (0.5 if column_counts else 0.0)

		return {
			'grid': {
				'detected_grids': grids[:20],
				'column_counts': sorted(set(column_counts)),
				'alignment_score': alignment,
				'gutter_px': sorted(set(round(g, 1) for g in gutters))[:12],
				'issues': issues,
			},
		}
