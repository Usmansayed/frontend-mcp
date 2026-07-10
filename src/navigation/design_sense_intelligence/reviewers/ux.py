"""UX specialist reviewer."""
from __future__ import annotations

from ..models import FindingSeverity, QualityPillar, ReviewFinding, ReviewRequest


class UXReviewer:
	name = 'ux_reviewer'
	category = 'ux'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		findings: list[ReviewFinding] = []
		if request.user_task:
			findings.append(
				ReviewFinding(
					id='ux_task_identified',
					category='ux',
					severity=FindingSeverity.ADVISORY.value,
					message=f'Primary user task: {request.user_task}',
					rationale='Frictionless pillar — task clarity established',
					source=self.name,
					pillar=QualityPillar.FRICTIONLESS.value,
				)
			)
		else:
			findings.append(
				ReviewFinding(
					id='ux_missing_task',
					category='ux',
					severity=FindingSeverity.MAJOR.value,
					message='Define primary user task before UX critique',
					source=self.name,
					pillar=QualityPillar.FRICTIONLESS.value,
				)
			)
		return findings
