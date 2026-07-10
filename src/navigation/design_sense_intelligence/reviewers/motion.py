"""Motion specialist reviewer."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


class MotionReviewer:
	name = 'motion_reviewer'
	category = 'motion'
	lane = 'subjective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		# Placeholder — future: prefers-reduced-motion, animation duration audit
		return []
