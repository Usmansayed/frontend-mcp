"""Color specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


class ColorReviewer:
	name = 'color_reviewer'
	category = 'color'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		# Placeholder — future: contrast ratios from computed styles
		if not request.computed_styles:
			return [
				ReviewFinding(
					id='color_awaiting_styles',
					category='color',
					severity='advisory',
					message='Color review awaiting computed styles for contrast analysis',
					source=self.name,
				)
			]
		return []
