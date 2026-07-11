"""Motion extractor — transitions and animations."""
from __future__ import annotations

import re
from typing import Any

from ..raw_context import RawBrowserContext
from ._utils import element_style, unique_sorted

_DURATION_RE = re.compile(r'(\d+(?:\.\d+)?)(m?s)')


def _parse_duration_ms(value: str | None) -> float | None:
	if not value or value == 'none':
		return None
	m = _DURATION_RE.search(str(value))
	if not m:
		return None
	num = float(m.group(1))
	unit = m.group(2)
	return num if unit == 'ms' else num * 1000.0


class MotionExtractor:
	name = 'motion'

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		transitions: list[dict[str, Any]] = []
		animations: list[dict[str, Any]] = []
		durations: list[float] = []
		issues: list[dict[str, Any]] = []

		for el in context.elements[:60]:
			style = element_style(el)
			tr = style.get('transition')
			an = style.get('animation')
			ad = style.get('animationDuration')
			if tr and tr != 'none':
				ms = _parse_duration_ms(tr)
				if ms is not None:
					durations.append(ms)
				transitions.append({'tag': el.get('tag'), 'transition': tr})
			if an and an != 'none':
				ms = _parse_duration_ms(ad or an)
				if ms is not None:
					durations.append(ms)
				animations.append({'tag': el.get('tag'), 'animation': an})
				if ms and ms > 500 and len(issues) < 10:
					issues.append({
						'kind': 'slow_animation',
						'severity': 'advisory',
						'detail': f'{ms}ms on {el.get("tag")}',
					})

		if context.prefers_reduced_motion and (transitions or animations):
			issues.append({
				'kind': 'motion_with_reduced_motion_pref',
				'severity': 'advisory',
				'detail': 'User prefers reduced motion but animations detected',
			})

		return {
			'motion': {
				'transitions': transitions[:20],
				'animations': animations[:20],
				'duration_ms': unique_sorted(durations),
				'prefers_reduced_motion': context.prefers_reduced_motion,
				'issues': issues,
			},
		}
