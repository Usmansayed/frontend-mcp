"""Typography specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ._helpers import findings_from_visual_insights


class TypographyReviewer:
	name = 'typography_reviewer'
	category = 'typography'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		return findings_from_visual_insights(
			request, category='typography', source=self.name, kind_filter='truncat'
		)
