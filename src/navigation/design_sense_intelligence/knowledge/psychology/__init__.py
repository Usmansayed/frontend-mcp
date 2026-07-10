"""Psychology-informed UX hints."""
from __future__ import annotations

from ...models import ReviewRequest

PSYCHOLOGY_HINTS = [
	{
		'id': 'cognitive_load',
		'trigger': lambda r: r.scope in ('flow', 'feature'),
		'text': 'Reduce cognitive load — limit choices per step',
	},
	{
		'id': 'hicks_law',
		'trigger': lambda r: 'checkout' in (r.user_task or '').lower(),
		'text': "Hick's Law — minimize decision points during checkout",
	},
]


def get_psychology_hints(request: ReviewRequest) -> list[dict]:
	return [h for h in PSYCHOLOGY_HINTS if h['trigger'](request)]
