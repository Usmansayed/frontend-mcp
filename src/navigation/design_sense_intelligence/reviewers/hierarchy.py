"""Visual hierarchy specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


class HierarchyReviewer:
	name = 'hierarchy_reviewer'
	category = 'hierarchy'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		boxes = (request.visual_insights or {}).get('boxes') or []
		if len(boxes) > 40:
			return [
				ReviewFinding(
					id='hierarchy_dense_ui',
					category='hierarchy',
					severity='minor',
					message=f'High interactive element density ({len(boxes)} regions) — check visual hierarchy',
					recommendation='Ensure primary action stands out; reduce competing focal points',
					source=self.name,
				)
			]
		return []
