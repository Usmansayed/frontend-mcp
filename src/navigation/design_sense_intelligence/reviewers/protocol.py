"""Specialist reviewer protocol — Crit/Rams-inspired replaceable experts."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import ReviewFinding, ReviewRequest


@runtime_checkable
class SpecialistReviewer(Protocol):
	name: str
	category: str
	lane: str  # objective | subjective

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		"""Return category-specific findings."""
