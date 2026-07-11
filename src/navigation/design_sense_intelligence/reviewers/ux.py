"""UX specialist reviewer."""
from __future__ import annotations

from ..models import FindingSeverity, QualityPillar, ReviewFinding, ReviewRequest


class UXReviewer:
	name = 'ux_reviewer'
	category = 'ux'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		if not request.user_task:
			return [
				ReviewFinding(
					id='ux_missing_task',
					category='ux',
					severity=FindingSeverity.MAJOR.value,
					message='Define primary user task before UX critique',
					rationale='Cannot evaluate task completion without a stated user goal',
					recommendation='Provide user_task in the review request',
					source=self.name,
					pillar=QualityPillar.FRICTIONLESS.value,
					confidence=0.7,
					confirmed=True,
				)
			]
		return []
