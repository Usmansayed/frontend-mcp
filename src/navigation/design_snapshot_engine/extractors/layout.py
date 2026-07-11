"""Layout extractor — viewport, overflow, visual insights."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext


class LayoutExtractor:
	name = 'layout'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		vp = context.viewport
		doc = context.document
		visual = dict(context.visual_insights or {})
		issues = list(visual.get('issues') or [])
		overflow_issues = [i for i in issues if 'overflow' in str(i.get('kind', ''))]
		interactive = list(visual.get('element_boxes') or [])

		if doc.get('scrollWidth', 0) > vp.get('width', 0) + 2 and not overflow_issues:
			overflow_issues.append({
				'kind': 'horizontal_overflow',
				'severity': 'blocking',
				'detail': f"scrollWidth={doc.get('scrollWidth')} viewport={vp.get('width')}",
			})

		regions: list[dict[str, Any]] = []
		layout_tree: list[dict[str, Any]] = []
		for tag in ('header', 'nav', 'main', 'footer', 'form'):
			for el in context.elements:
				if el.get('tag') == tag:
					node = {
						'role': tag,
						'rect': el.get('rect'),
						'text': el.get('text', '')[:40],
						'children_count': 0,
					}
					regions.append(node)
					layout_tree.append({**node, 'depth': 0})
					break

		# Shallow tree from heading + section hierarchy
		for el in context.elements:
			tag = el.get('tag', '')
			if tag in ('section', 'article', 'div', 'main') and el.get('rect'):
				layout_tree.append({
					'tag': tag,
					'depth': 1 if tag in ('section', 'article') else 2,
					'rect': el.get('rect'),
					'classes': (el.get('classes') or [])[:3],
				})
				if len(layout_tree) >= 24:
					break

		return {
			'layout': {
				'viewport': vp,
				'document_size': doc,
				'visual_insights': visual,
				'layout_tree': layout_tree[:24],
				'regions': regions,
				'interactive_boxes': interactive[:60],
				'overflow_issues': overflow_issues,
				'issues': issues[:30],
			},
		}
