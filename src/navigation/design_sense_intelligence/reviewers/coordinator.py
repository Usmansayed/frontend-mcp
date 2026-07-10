"""Review Coordinator — objective/subjective lanes → reasoning → merge."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from ..models import (
	DesignReviewReport,
	DimensionScore,
	LaneReviewBundle,
	ProviderContribution,
	QualityPillar,
	ReviewFinding,
	ReviewLane,
	ReviewRequest,
)
from ..providers.registry import ProviderRegistry
from ..reasoning.engine import ReasoningEngine
from ..workflows.review_workflow import MICROSOFT_REVIEW_PHASES
from .accessibility import AccessibilityReviewer
from .color import ColorReviewer
from .component import ComponentReviewer
from .hierarchy import HierarchyReviewer
from .layout import LayoutReviewer
from .motion import MotionReviewer
from .navigation import NavigationReviewer
from .protocol import SpecialistReviewer
from .typography import TypographyReviewer
from .ux import UXReviewer


_SEVERITY_ORDER = {'blocking': 0, 'major': 1, 'minor': 2, 'advisory': 3}


def default_reviewers() -> list[SpecialistReviewer]:
	return [
		LayoutReviewer(),
		TypographyReviewer(),
		ColorReviewer(),
		HierarchyReviewer(),
		NavigationReviewer(),
		ComponentReviewer(),
		UXReviewer(),
		AccessibilityReviewer(),
		MotionReviewer(),
	]


class ReviewCoordinator:
	"""Orchestrate lanes separately, reason, then merge."""

	def __init__(
		self,
		*,
		reviewers: list[SpecialistReviewer] | None = None,
		providers: ProviderRegistry | None = None,
		reasoning: ReasoningEngine | None = None,
	) -> None:
		self._reviewers = reviewers or default_reviewers()
		self._providers = providers or ProviderRegistry()
		self._reasoning = reasoning or ReasoningEngine()

	async def run(self, request: ReviewRequest) -> DesignReviewReport:
		degraded: list[str] = []
		consulted_reviewers: list[str] = []

		objective_bundle = await self._run_reviewer_lane(
			request,
			lane=ReviewLane.OBJECTIVE.value,
			degraded=degraded,
			consulted=consulted_reviewers,
		)
		subjective_bundle = await self._run_reviewer_lane(
			request,
			lane=ReviewLane.SUBJECTIVE.value,
			degraded=degraded,
			consulted=consulted_reviewers,
		)

		obj_providers = await self._providers.collect_objective(request)
		sub_providers = await self._providers.collect_subjective(request)
		consulted_providers: list[str] = []

		_apply_provider_contributions(objective_bundle, obj_providers, consulted_providers, degraded)
		_apply_provider_contributions(subjective_bundle, sub_providers, consulted_providers, degraded)

		knowledge_notes = [
			n for c in sub_providers if c.provider == 'design_knowledge' for n in c.notes
		]
		scores = subjective_bundle.scores

		reasoning = self._reasoning.synthesize(
			request,
			objective_findings=objective_bundle.findings,
			subjective_findings=subjective_bundle.findings,
			scores=scores,
			knowledge_notes=knowledge_notes,
		)
		degraded.extend(reasoning.degraded)

		all_findings = _dedupe_findings(objective_bundle.findings + subjective_bundle.findings)
		all_findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f.severity, 9), f.category))

		pillars = _group_by_pillar(all_findings)
		blocking = [f for f in all_findings if f.severity == 'blocking']
		passed = not blocking

		summary = reasoning.narrative or _build_summary(all_findings, scores)

		return DesignReviewReport(
			passed=passed,
			summary=summary,
			findings=all_findings,
			objective_findings=list(objective_bundle.findings),
			subjective_findings=list(subjective_bundle.findings),
			scores=scores,
			pillars=pillars,
			reasoning=reasoning,
			consulted_providers=consulted_providers,
			consulted_reviewers=consulted_reviewers,
			workflow_phases=list(MICROSOFT_REVIEW_PHASES),
			degraded=list(dict.fromkeys(degraded)),
		)

	async def _run_reviewer_lane(
		self,
		request: ReviewRequest,
		*,
		lane: str,
		degraded: list[str],
		consulted: list[str],
	) -> LaneReviewBundle:
		reviewers = [r for r in self._reviewers if r.lane == lane]
		results = await asyncio.gather(
			*[r.review(request) for r in reviewers],
			return_exceptions=True,
		)
		findings: list[ReviewFinding] = []
		for reviewer, result in zip(reviewers, results, strict=True):
			consulted.append(reviewer.name)
			if isinstance(result, Exception):
				degraded.append(f'{reviewer.name}_error:{type(result).__name__}')
				continue
			findings.extend(result)
		return LaneReviewBundle(lane=lane, findings=findings)


def _apply_provider_contributions(
	bundle: LaneReviewBundle,
	contributions: list[ProviderContribution],
	consulted_providers: list[str],
	degraded: list[str],
) -> None:
	for contrib in contributions:
		consulted_providers.append(contrib.provider)
		bundle.findings.extend(contrib.findings)
		bundle.scores.extend(contrib.scores)
		bundle.notes.extend(contrib.notes)
		degraded.extend(contrib.degraded)


def _dedupe_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
	seen: set[str] = set()
	out: list[ReviewFinding] = []
	for f in findings:
		key = f.id or f'{f.category}:{f.message}'
		if key in seen:
			continue
		seen.add(key)
		out.append(f)
	return out


def _group_by_pillar(findings: list[ReviewFinding]) -> dict[str, list[str]]:
	pillars: dict[str, list[str]] = defaultdict(list)
	for f in findings:
		pillar = f.pillar or QualityPillar.CRAFT.value
		pillars[pillar].append(f.message)
	return dict(pillars)


def _build_summary(findings: list[ReviewFinding], scores: list[DimensionScore]) -> str:
	blocking = sum(1 for f in findings if f.severity == 'blocking')
	major = sum(1 for f in findings if f.severity == 'major')
	score_note = ''
	if scores:
		overall = next((s for s in scores if s.dimension == 'overall'), None)
		if overall:
			score_note = f' Overall score {overall.score}/{10 if overall.scale == "scale_10" else 5}.'
	return (
		f'Design review: {len(findings)} findings '
		f'({blocking} blocking, {major} major).{score_note}'
	).strip()
