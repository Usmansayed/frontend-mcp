"""Accessibility specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ._helpers import findings_from_visual_insights


class AccessibilityReviewer:
	name = 'accessibility_reviewer'
	category = 'accessibility'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		findings = findings_from_visual_insights(
			request, category='accessibility', source=self.name, kind_filter='zero_size'
		)
		findings.extend(
			findings_from_visual_insights(
				request, category='accessibility', source=self.name, kind_filter='clickable'
			)
		)
		return findings
