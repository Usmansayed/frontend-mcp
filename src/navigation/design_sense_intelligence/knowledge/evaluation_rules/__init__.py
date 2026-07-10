"""Evaluation rules derived from internal knowledge (subjective lane)."""
from __future__ import annotations

from ...models import ReviewFinding, ReviewRequest


def evaluate_against_rules(request: ReviewRequest) -> list[ReviewFinding]:
	"""Placeholder — future: knowledge-backed qualitative rules."""
	_ = request
	return []
