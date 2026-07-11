"""Component extractor — interactive controls and UI patterns."""
from __future__ import annotations

from typing import Any

from ..raw_context import RawBrowserContext

_INTERACTIVE = frozenset({'button', 'a', 'input', 'select', 'textarea', 'label'})
_PATTERNS = (
	('form', frozenset({'form'})),
	('card', frozenset({'card'})),
	('navigation', frozenset({'nav'})),
	('primary_cta', frozenset({'primary'})),
)


class ComponentExtractor:
	name = 'components'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		nodes: list[dict[str, Any]] = []
		form_controls: list[dict[str, Any]] = []
		pattern_hits: dict[str, int] = {p[0]: 0 for p in _PATTERNS}
		issues: list[dict[str, Any]] = []
		interactive = 0

		for el in context.elements:
			tag = str(el.get('tag') or '')
			classes = set(el.get('classes') or [])
			if tag in _INTERACTIVE or el.get('role') in ('button', 'link'):
				interactive += 1
				nodes.append({
					'tag': tag,
					'role': el.get('role'),
					'text': el.get('text', '')[:48],
					'classes': list(classes)[:6],
					'rect': el.get('rect'),
				})
			if tag in ('input', 'select', 'textarea', 'button'):
				form_controls.append({
					'tag': tag,
					'text': el.get('text', '')[:40],
					'ariaLabel': el.get('ariaLabel'),
				})

			for name, class_hints in _PATTERNS:
				if tag in class_hints or classes & class_hints:
					pattern_hits[name] += 1

		patterns = [{'name': k, 'count': v} for k, v in pattern_hits.items() if v > 0]

		return {
			'components': {
				'nodes': nodes[:40],
				'patterns': patterns,
				'interactive_count': interactive,
				'form_controls': form_controls[:20],
				'issues': issues,
			},
		}
