"""Synthesize cross-module guidance into foundation ranking — no fixed weights."""
from __future__ import annotations

from ..integration_models import (
	CandidateGuidance,
	CodebaseGuidance,
	ConsistencyGuidance,
	DesignSenseGuidance,
	FrameworkGuidance,
	SynthesisResult,
)
from ..models import ComponentCandidate, ParsedQuery


def synthesize_guidance(
	candidate: ComponentCandidate,
	framework: FrameworkGuidance,
	codebase: CodebaseGuidance,
	design_sense: DesignSenseGuidance,
	consistency: ConsistencyGuidance,
	*,
	parsed_query: ParsedQuery | None = None,
) -> SynthesisResult:
	"""Merge module opinions into eligibility, concerns, strengths, and rank factors."""
	strengths: list[str] = []
	concerns: list[str] = []

	if not framework.compatible:
		concerns.extend(framework.issues or ['framework_incompatible'])
		return SynthesisResult(
			eligible=False,
			summary=f'{candidate.title} blocked by framework compatibility',
			strengths=strengths,
			concerns=concerns,
			rank_factors={'framework_compatible': False},
		)

	if framework.compatibility_warnings:
		concerns.extend(framework.compatibility_warnings)
	else:
		strengths.append('No framework compatibility warnings')

	if codebase.duplicate_risks:
		concerns.extend(codebase.duplicate_risks)
	if codebase.preferred_implementations:
		strengths.append('Matches preferred codebase patterns')
	if codebase.reusable_utilities:
		strengths.append(f'Reuses utilities: {", ".join(codebase.reusable_utilities[:3])}')

	design_match = _query_design_alignment(design_sense, parsed_query)
	if design_match > 0:
		strengths.append(design_sense.ux_recommendation or 'Strong UX alignment with request')
	elif design_sense.notes:
		concerns.extend(design_sense.notes)

	mod_count = len(consistency.all_adjustments())
	if mod_count == 0:
		strengths.append('Minimal consistency adjustments required')
	else:
		concerns.append(f'{mod_count} consistency adjustment(s) recommended')

	rank_factors = {
		'framework_compatible': True,
		'framework_issue_count': len(framework.issues),
		'warning_count': len(framework.compatibility_warnings),
		'design_alignment': design_match,
		'consistency_adjustment_count': mod_count,
		'duplicate_risk_count': len(codebase.duplicate_risks),
		'search_relevance': candidate.relevance_score,
	}

	summary = (
		f'Foundation candidate {candidate.title}: '
		f'{len(strengths)} strength(s), {len(concerns)} concern(s)'
	)
	return SynthesisResult(
		eligible=True,
		summary=summary,
		strengths=strengths,
		concerns=concerns,
		rank_factors=rank_factors,
	)


def rank_key(
	candidate: ComponentCandidate,
	guidance: CandidateGuidance,
) -> tuple:
	"""Deterministic sort key — priority rules, not percentage weights."""
	if not guidance.synthesis.eligible:
		return (1, 0, 0, 0, 0, 0, 0)
	f = guidance.synthesis.rank_factors
	return (
		0,
		int(f.get('framework_issue_count', 0)),
		int(f.get('warning_count', 0)),
		-int(f.get('design_alignment', 0)),
		int(f.get('consistency_adjustment_count', 0)),
		int(f.get('duplicate_risk_count', 0)),
		-float(f.get('search_relevance', 0)),
	)


def _query_design_alignment(design: DesignSenseGuidance, parsed_query: ParsedQuery | None) -> int:
	if not parsed_query:
		return 0 if not design.ux_recommendation else 1
	score = 0
	if parsed_query.page_context and design.layout_recommendation:
		score += 1
	if parsed_query.animations and design.interaction_recommendation:
		score += 1
	if design.ux_recommendation and design.ux_recommendation != 'neutral':
		score += 1
	return score
