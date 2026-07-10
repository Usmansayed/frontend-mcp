"""Reasoning engine — synthesizes reviewer + provider outputs into coherent critique."""
from __future__ import annotations

from collections import Counter

from ..models import DimensionScore, ReasoningResult, ReviewFinding, ReviewRequest


class ReasoningEngine:
	"""Sits between lane bundles and coordinator merge — produces narrative synthesis."""

	def synthesize(
		self,
		request: ReviewRequest,
		*,
		objective_findings: list[ReviewFinding],
		subjective_findings: list[ReviewFinding],
		scores: list[DimensionScore],
		knowledge_notes: list[str],
	) -> ReasoningResult:
		degraded = ['reasoning_engine_heuristic']
		all_findings = objective_findings + subjective_findings

		themes = _top_categories(all_findings)
		strengths = _extract_strengths(request, scores, objective_findings)
		concerns = _extract_concerns(all_findings)
		recommendations = _build_recommendations(all_findings, knowledge_notes)

		task = request.user_task or 'the interface'
		narrative = _compose_narrative(
			task=task,
			themes=themes,
			strengths=strengths,
			concerns=concerns,
			recommendations=recommendations,
			objective_count=len(objective_findings),
			subjective_count=len(subjective_findings),
		)

		return ReasoningResult(
			narrative=narrative,
			themes=themes,
			strengths=strengths,
			concerns=concerns,
			recommendations=recommendations,
			degraded=degraded,
		)


def _top_categories(findings: list[ReviewFinding], limit: int = 5) -> list[str]:
	counts = Counter(f.category for f in findings)
	return [cat for cat, _ in counts.most_common(limit)]


def _extract_strengths(
	request: ReviewRequest,
	scores: list[DimensionScore],
	objective_findings: list[ReviewFinding],
) -> list[str]:
	strengths: list[str] = []
	if request.user_task:
		strengths.append(f'User task is explicit: {request.user_task}')
	blocking_objective = [f for f in objective_findings if f.severity == 'blocking']
	if not blocking_objective and objective_findings:
		strengths.append('No blocking objective violations detected')
	for score in scores:
		if score.dimension == 'overall' and score.score >= 7.0:
			strengths.append(f'Strong overall quality signal ({score.score})')
	return strengths[:5]


def _extract_concerns(findings: list[ReviewFinding]) -> list[str]:
	priority = {'blocking': 0, 'major': 1, 'minor': 2, 'advisory': 3}
	sorted_f = sorted(findings, key=lambda f: priority.get(f.severity, 9))
	return [f.message for f in sorted_f[:8]]


def _build_recommendations(findings: list[ReviewFinding], knowledge_notes: list[str]) -> list[str]:
	recs: list[str] = []
	for f in findings:
		if f.recommendation and f.recommendation not in recs:
			recs.append(f.recommendation)
		if len(recs) >= 6:
			break
	for note in knowledge_notes[:3]:
		if note.startswith('recommend:'):
			recs.append(note.removeprefix('recommend:').strip())
	return recs[:8]


def _compose_narrative(
	*,
	task: str,
	themes: list[str],
	strengths: list[str],
	concerns: list[str],
	recommendations: list[str],
	objective_count: int,
	subjective_count: int,
) -> str:
	parts = [
		f'For "{task}", the review combined {objective_count} objective and '
		f'{subjective_count} subjective signals.',
	]
	if themes:
		parts.append(f'Primary themes: {", ".join(themes)}.')
	if strengths:
		parts.append(f'Strengths: {"; ".join(strengths[:2])}.')
	if concerns:
		parts.append(f'Top concerns: {"; ".join(concerns[:3])}.')
	if recommendations:
		parts.append(f'Prioritized recommendations: {"; ".join(recommendations[:3])}.')
	return ' '.join(parts)
