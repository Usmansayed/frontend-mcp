"""Accessibility extractor — roles, labels, focusable elements."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext

_INTERACTIVE = frozenset({'button', 'a', 'input', 'select', 'textarea'})


class AccessibilityExtractor:
	name = 'accessibility'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		roles: list[dict[str, Any]] = []
		unlabeled: list[dict[str, Any]] = []
		aria_usage: set[str] = set()
		issues: list[dict[str, Any]] = []
		focusable = 0

		for el in context.elements:
			tag = str(el.get('tag') or '')
			role = el.get('role') or tag
			if role:
				roles.append({'role': role, 'tag': tag, 'text': el.get('text', '')[:40]})
			if el.get('ariaLabel'):
				aria_usage.add('aria-label')

			if tag in _INTERACTIVE or el.get('role') in ('button', 'link', 'textbox'):
				focusable += 1
				label = el.get('ariaLabel') or el.get('text', '')
				if not str(label).strip() and tag != 'input':
					unlabeled.append({
						'tag': tag,
						'role': el.get('role'),
						'classes': el.get('classes', [])[:4],
					})
					if len(issues) < 15:
						issues.append({
							'kind': 'unlabeled_interactive',
							'severity': 'major',
							'detail': f'{tag} without accessible name',
						})

		# Pull contrast failures from color section via layout issues if present
		for issue in (context.visual_insights or {}).get('issues') or []:
			if issue.get('kind') == 'zero_size_clickable':
				issues.append({**issue, 'source': 'visual_insights'})

		return {
			'accessibility': {
				'roles': roles[:40],
				'unlabeled_interactive': unlabeled[:20],
				'focusable_count': focusable,
				'aria_usage': sorted(aria_usage),
				'issues': issues[:25],
			},
		}
