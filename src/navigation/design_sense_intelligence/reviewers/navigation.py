"""Navigation specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


class NavigationReviewer:
	name = 'navigation_reviewer'
	category = 'navigation'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		if request.scope in ('flow', 'feature') and not request.user_task:
			return [
				ReviewFinding(
					id='nav_missing_task',
					category='navigation',
					severity='major',
					message='Flow/feature review needs user_task to evaluate navigation clarity',
					source=self.name,
				)
			]
		return []
