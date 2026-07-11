"""Psychology laws and cognitive principles — from epistemology research."""
from __future__ import annotations

from ...models import ReviewRequest
from ..epistemology import PSYCHOLOGY_LAWS
from ..types import PsychologyLaw

__all__ = ['PSYCHOLOGY_LAWS', 'PsychologyLaw', 'get_psychology_hints']


_TASK_LAW_TRIGGERS: dict[str, list[str]] = {
	'checkout': ['hicks_law', 'cognitive_load'],
	'menu': ['hicks_law', 'millers_law'],
	'dashboard': ['millers_law', 'cognitive_load'],
	'mobile': ['fitts_law'],
	'form': ['cognitive_load', 'hicks_law'],
}


def get_psychology_hints(request: ReviewRequest) -> list[dict]:
	task = (request.user_task or '').lower()
	hints: list[dict] = []
	seen: set[str] = set()

	for keyword, law_ids in _TASK_LAW_TRIGGERS.items():
		if keyword not in task:
			continue
		for law in PSYCHOLOGY_LAWS:
			if law.id in law_ids and law.id not in seen:
				seen.add(law.id)
				hints.append({
					'id': law.id,
					'title': law.title,
					'formula': law.formula,
					'text': law.design_implication,
				})

	if request.scope in ('flow', 'feature') and 'cognitive_load' not in seen:
		law = next(l for l in PSYCHOLOGY_LAWS if l.id == 'cognitive_load')
		hints.append({
			'id': law.id,
			'title': law.title,
			'formula': law.formula,
			'text': law.design_implication,
		})

	return hints
