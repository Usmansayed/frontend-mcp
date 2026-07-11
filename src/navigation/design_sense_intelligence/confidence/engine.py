"""Confidence engine — evidence + rules + agreement + reference support."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import ReviewFinding

DEFAULT_CONFIDENCE_THRESHOLD = 0.55


@dataclass(slots=True)
class ConfidenceContext:
	"""Signals used to score finding confidence."""

	reference_note_count: int = 0
	has_snapshot: bool = False
	user_task: str = ''


@dataclass(slots=True)
class ConfidenceResult:
	findings: list[ReviewFinding] = field(default_factory=list)
	suppressed_count: int = 0
	threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'findings': [f.to_dict() for f in self.findings],
			'suppressed_count': self.suppressed_count,
			'threshold': self.threshold,
			'degraded': list(self.degraded),
		}


class ConfidenceEngine:
	"""Score findings and suppress below threshold."""

	def __init__(self, *, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
		self._threshold = threshold

	def apply(
		self,
		findings: list[ReviewFinding],
		*,
		context: ConfidenceContext | None = None,
	) -> ConfidenceResult:
		ctx = context or ConfidenceContext()
		kept: list[ReviewFinding] = []
		suppressed = 0

		for f in findings:
			score = compute_confidence(f, ctx)
			meta = dict(f.metadata)
			meta['confidence_score'] = round(score, 3)
			scored = ReviewFinding(
				id=f.id,
				category=f.category,
				severity=f.severity,
				message=f.message,
				rationale=f.rationale,
				recommendation=f.recommendation,
				source=f.source,
				pillar=f.pillar,
				selector=f.selector,
				region=f.region,
				evidence=f.evidence,
				confidence=max(f.confidence, score),
				confirmed=f.confirmed,
				affected_element=f.affected_element,
				metadata=meta,
			)
			if score < self._threshold and f.severity not in ('blocking',):
				suppressed += 1
				continue
			kept.append(scored)

		return ConfidenceResult(
			findings=kept,
			suppressed_count=suppressed,
			threshold=self._threshold,
			degraded=['confidence_engine_v1'],
		)


def compute_confidence(finding: ReviewFinding, ctx: ConfidenceContext) -> float:
	"""Evidence + rules + cross-reviewer agreement + reference support."""
	score = 0.0

	if finding.evidence:
		score += 0.35
	if finding.rationale:
		score += 0.12
	if finding.affected_element or finding.selector:
		score += 0.15
	if finding.recommendation:
		score += 0.08

	if finding.confirmed:
		score += 0.10

	sources = finding.metadata.get('consensus_sources') or []
	if isinstance(sources, list) and len(sources) > 1:
		score += 0.15
	elif finding.metadata.get('merged_from', 1) > 1:
		score += 0.12

	if finding.severity == 'blocking':
		score += 0.15
	elif finding.severity == 'major':
		score += 0.08

	if ctx.reference_note_count and _references_finding(finding):
		score += 0.10

	if ctx.has_snapshot and finding.evidence:
		score += 0.05

	return min(1.0, max(finding.confidence, score))


def _references_finding(finding: ReviewFinding) -> bool:
	msg = finding.message.lower()
	return any(
		kw in msg
		for kw in ('token', 'spacing', 'typography', 'palette', 'font', 'color')
	)
