"""Core design principles — expand via Gemini research."""
from __future__ import annotations

from ...models import FindingSeverity, ReviewFinding, ReviewRequest

PRINCIPLES = [
	{
		'id': 'clear_hierarchy',
		'title': 'Clear visual hierarchy',
		'when': lambda r: r.scope in ('page', 'feature'),
		'message': 'Establish a single primary focal point per viewport',
	},
	{
		'id': 'progressive_disclosure',
		'title': 'Progressive disclosure',
		'when': lambda r: r.scope == 'flow',
		'message': 'Reveal complexity gradually across flow steps',
	},
	{
		'id': 'recognition_over_recall',
		'title': 'Recognition over recall',
		'when': lambda r: bool(r.user_task),
		'message': 'Make options visible rather than requiring memory',
	},
]


def get_applicable_principles(request: ReviewRequest) -> list[dict]:
	out: list[dict] = []
	for p in PRINCIPLES:
		if not p['when'](request):
			continue
		entry = {'id': p['id'], 'title': p['title']}
		if request.user_task and p['id'] == 'recognition_over_recall':
			entry['finding'] = ReviewFinding(
				id=f'principle_{p["id"]}',
				category='ux',
				severity=FindingSeverity.ADVISORY.value,
				message=p['message'],
				rationale=p['title'],
				source='design_knowledge',
			)
		out.append(entry)
	return out
