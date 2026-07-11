"""Layout specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ._helpers import findings_from_visual_insights


class LayoutReviewer:
	name = 'layout_reviewer'
	category = 'layout'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		return findings_from_visual_insights(
			request, category='layout', source=self.name, kind_filter='overflow'
		)
