"""Accessibility specialist reviewer — reasons over AccessibilitySnapshot."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ..snapshot_access import resolve_snapshot
from ._helpers import findings_from_visual_insights


class AccessibilityReviewer:
	name = 'accessibility_reviewer'
	category = 'accessibility'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		snapshot = resolve_snapshot(request)
		if snapshot is not None:
			findings: list[ReviewFinding] = []
			for i, issue in enumerate(snapshot.accessibility.issues[:12]):
				kind = str(issue.get('kind', 'accessibility issue'))
				findings.append(
					ReviewFinding(
						id=f'a11y_snapshot_{i}',
						category='accessibility',
						severity=str(issue.get('severity', 'major')),
						message=str(issue.get('detail', kind)),
						rationale=f'Snapshot accessibility scan detected {kind}',
						recommendation=str(issue.get('recommendation', '')),
						source=self.name,
						selector=issue.get('selector'),
						affected_element=issue.get('selector') or issue.get('tag'),
						evidence=f'a11y kind={kind} detail={issue.get("detail", "")}',
						confidence=0.88,
						confirmed=True,
					)
				)
			if snapshot.accessibility.unlabeled_interactive:
				count = len(snapshot.accessibility.unlabeled_interactive)
				findings.append(
					ReviewFinding(
						id='a11y_unlabeled_count',
						category='accessibility',
						severity='major',
						message=f'{count} interactive elements lack accessible names',
						rationale='Controls without visible text or aria-label fail WCAG name requirements',
						recommendation='Add aria-label or visible text to interactive controls',
						source=self.name,
						evidence=f'unlabeled_interactive_count={count}',
						confidence=0.9,
						confirmed=True,
					)
				)
			if findings:
				return findings

		findings = findings_from_visual_insights(
			request, category='accessibility', source=self.name, kind_filter='zero_size'
		)
		findings.extend(
			findings_from_visual_insights(
				request, category='accessibility', source=self.name, kind_filter='clickable'
			)
		)
		return findings
