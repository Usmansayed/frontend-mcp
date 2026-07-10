"""Learning layer — store feedback, examples, benchmarks for future improvement."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewFeedback:
	"""Human or agent feedback on a past review."""

	review_id: str
	accepted_findings: list[str] = field(default_factory=list)
	rejected_findings: list[str] = field(default_factory=list)
	notes: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'review_id': self.review_id,
			'accepted_findings': list(self.accepted_findings),
			'rejected_findings': list(self.rejected_findings),
			'notes': self.notes,
		}


class LearningStore:
	"""In-memory scaffold — future: persist feedback/examples/benchmarks."""

	def __init__(self) -> None:
		self.feedback: list[ReviewFeedback] = []
		self.examples: list[dict[str, Any]] = []
		self.benchmarks: list[dict[str, Any]] = []

	def record_feedback(self, feedback: ReviewFeedback) -> None:
		self.feedback.append(feedback)
