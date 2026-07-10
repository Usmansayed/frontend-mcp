"""Component specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


class ComponentReviewer:
	name = 'component_reviewer'
	category = 'component'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		meta = request.component_metadata or {}
		if meta and not meta.get('design_system_match'):
			return [
				ReviewFinding(
					id='component_ds_mismatch',
					category='component',
					severity='minor',
					message='Component metadata suggests possible design-system mismatch',
					source=self.name,
				)
			]
		return []
