"""Layout specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ._helpers import findings_from_visual_insights


class LayoutReviewer:
	name = 'layout_reviewer'
	category = 'layout'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		findings = findings_from_visual_insights(
			request, category='layout', source=self.name, kind_filter='overflow'
		)
		if not findings and not request.dom_snapshot:
			findings.append(
				ReviewFinding(
					id='layout_awaiting_dom',
					category='layout',
					severity='advisory',
					message='Layout review awaiting DOM snapshot or visual insights',
					source=self.name,
				)
			)
		return findings
