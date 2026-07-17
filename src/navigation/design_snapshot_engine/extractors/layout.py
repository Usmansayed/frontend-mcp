"""Layout extractor — viewport, overflow, visual insights, enriched regions."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style


def _region_width_ratio(rect: dict[str, Any] | None, viewport_w: float) -> float | None:
	if not rect or viewport_w <= 0:
		return None
	w = float(rect.get('w') or rect.get('width') or 0)
	if w <= 0:
		return None
	return round(min(1.0, w / viewport_w), 4)


def _region_centered(rect: dict[str, Any] | None, viewport_w: float) -> bool:
	if not rect or viewport_w <= 0:
		return False
	x = float(rect.get('x') or rect.get('left') or 0)
	w = float(rect.get('w') or rect.get('width') or 0)
	if w <= 0:
		return False
	left_margin = x
	right_margin = viewport_w - (x + w)
	# Centered if side margins are similar and content is not full-bleed.
	if w / viewport_w > 0.88:
		return False
	return abs(left_margin - right_margin) <= max(48.0, viewport_w * 0.08)


def _infer_nav_label(el: dict[str, Any]) -> str:
	role = str(el.get('role') or '').lower()
	classes = ' '.join(el.get('classes') or []).lower()
	tag = str(el.get('tag') or '').lower()
	if role in {'navigation', 'nav'} or 'sidebar' in classes or 'side-nav' in classes:
		return 'sidebar' if 'sidebar' in classes or tag == 'aside' else 'nav'
	if tag in {'nav', 'aside'}:
		return 'sidebar' if tag == 'aside' or 'sidebar' in classes else 'nav'
	return tag


class LayoutExtractor:
	name = 'layout'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		vp = context.viewport
		doc = context.document
		visual = dict(context.visual_insights or {})
		issues = list(visual.get('issues') or [])
		overflow_issues = [i for i in issues if 'overflow' in str(i.get('kind', ''))]
		interactive = list(visual.get('element_boxes') or [])

		vp_w = float(vp.get('width') or 0)
		if doc.get('scrollWidth', 0) > vp.get('width', 0) + 2 and not overflow_issues:
			overflow_issues.append({
				'kind': 'horizontal_overflow',
				'severity': 'blocking',
				'detail': f"scrollWidth={doc.get('scrollWidth')} viewport={vp.get('width')}",
			})

		regions: list[dict[str, Any]] = []
		layout_tree: list[dict[str, Any]] = []
		seen_roles: set[str] = set()
		region_tags = ('header', 'nav', 'aside', 'main', 'footer', 'form', 'section')
		for el in context.elements:
			tag = str(el.get('tag') or '')
			aria_role = str(el.get('role') or '').lower()
			classes = [str(c).lower() for c in (el.get('classes') or [])]
			is_navish = (
				tag in {'nav', 'aside'}
				or aria_role in {'navigation', 'complementary'}
				or any('sidebar' in c or 'side-nav' in c for c in classes)
			)
			if tag not in region_tags and not is_navish:
				continue
			if is_navish:
				role = tag if tag in {'nav', 'aside'} else 'nav'
				label = _infer_nav_label(el)
			else:
				role = tag
				label = tag
			# Prefer one primary region per role, but keep multiple sections.
			if role != 'section' and role in seen_roles:
				continue
			if role != 'section':
				seen_roles.add(role)

			style = element_style(el)
			rect = el.get('rect') if isinstance(el.get('rect'), dict) else {}
			position = str(style.get('position') or 'static').lower()
			width_ratio = _region_width_ratio(rect, vp_w)
			centered = _region_centered(rect, vp_w)
			layout_pattern = 'marketing_centered' if centered and (width_ratio or 1) <= 0.72 else None
			node = {
				'role': role,
				'label': label,
				'rect': rect,
				'text': el.get('text', '')[:40],
				'children_count': 0,
				'position': position,
				'width_ratio': width_ratio,
				'centered': centered,
				'layout_pattern': layout_pattern,
				'classes': classes[:5],
			}
			regions.append(node)
			layout_tree.append({**node, 'depth': 0})
			if len(regions) >= 24:
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
