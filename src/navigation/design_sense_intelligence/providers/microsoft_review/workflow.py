"""Microsoft Frontend Design Review Skill — methodology only (not integrated software).

Blueprint: identify user task → design system patterns → aesthetic direction →
scope → evaluate three pillars → score blocking/major/minor → recommend with examples.
"""
from __future__ import annotations

from ...models import (
	FindingSeverity,
	ProviderContribution,
	QualityPillar,
	ReviewFinding,
	ReviewRequest,
)
from ...workflows.review_workflow import MICROSOFT_REVIEW_PHASES, build_pillar_checklist


class MicrosoftReviewWorkflowProvider:
	name = 'microsoft_review'
	kind = 'methodology'
	lane = 'subjective'

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		findings: list[ReviewFinding] = []
		notes: list[str] = []
		degraded = ['microsoft_review_methodology']

		if not request.user_task:
			findings.append(
				ReviewFinding(
					id='ms_missing_user_task',
					category='workflow',
					severity=FindingSeverity.MAJOR.value,
					message='User task not specified — review should start by identifying the primary user task',
					rationale='Microsoft review workflow step 1: identify user task',
					recommendation='Provide user_task in ReviewRequest before critiquing UX',
					source=self.name,
					pillar=QualityPillar.FRICTIONLESS.value,
				)
			)

		checklist = build_pillar_checklist(request)
		for item in checklist:
			if item.get('flag'):
				findings.append(
					ReviewFinding(
						id=item['id'],
						category=item['category'],
						severity=item['severity'],
						message=item['message'],
						rationale=item.get('rationale', ''),
						recommendation=item.get('recommendation', ''),
						source=self.name,
						pillar=item.get('pillar'),
						evidence=f"visual_insights blocking={request.visual_insights.get('blocking', [])[:2] if request.visual_insights else []}",
						affected_element='page',
						confidence=0.9,
						confirmed=True,
					)
				)

		notes.extend(f'phase:{p}' for p in MICROSOFT_REVIEW_PHASES)

		return ProviderContribution(
			provider=self.name,
			findings=findings,
			notes=notes,
			degraded=degraded,
		)
