"""Hierarchy extractor — heading structure and prominence."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style, parse_px


class HierarchyExtractor:
	name = 'hierarchy'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		headings: list[dict[str, Any]] = []
		prominence: list[dict[str, Any]] = []
		skipped: list[str] = []
		issues: list[dict[str, Any]] = []

		for el in context.elements:
			tag = str(el.get('tag') or '')
			if tag.startswith('h') and len(tag) == 2 and tag[1].isdigit():
				level = int(tag[1])
				style = element_style(el)
				fs = parse_px(style.get('fontSize')) or 0
				raw_score = fs + level * 4
				headings.append({
					'level': level,
					'text': el.get('text', '')[:60],
					'font_size_px': fs,
				})
				prominence.append({
					'label': el.get('text', '')[:40] or tag,
					'score': raw_score,
					'level': level,
				})

		prev = 0
		for h in headings:
			lvl = h['level']
			if prev and lvl > prev + 1:
				skipped.append(f'h{prev}→h{lvl}')
				issues.append({
					'kind': 'skipped_heading_level',
					'severity': 'minor',
					'detail': f'Heading level jump h{prev} to h{lvl}',
				})
			prev = lvl

		prominence.sort(key=lambda p: -p['score'])
		max_score = max((float(p['score']) for p in prominence), default=0.0)
		for p in prominence:
			raw = float(p['score'])
			p['normalized'] = round(raw / max_score, 4) if max_score > 0 else 0.0
			p['prominence'] = p['normalized']

		return {
			'hierarchy': {
				'heading_tree': headings,
				'prominence_scores': prominence[:15],
				'skipped_levels': skipped,
				'issues': issues,
			},
		}
