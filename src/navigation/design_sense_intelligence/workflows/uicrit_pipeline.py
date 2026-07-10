"""UICrit-inspired critique pipeline (methodology reproduction)."""
from __future__ import annotations

from ..models import DimensionScore, ReviewFinding, ReviewRequest

UICRIT_DIMENSIONS = [
	('aesthetics', 'scale_10'),
	('learnability', 'likert_5'),
	('efficiency', 'likert_5'),
	('overall', 'scale_10'),
]

UICRIT_CATEGORIES = [
	'layout',
	'color_contrast',
	'text_readability',
	'button_usability',
	'learnability',
]


def run_uicrit_pipeline(request: ReviewRequest) -> dict:
	"""Stage critiques and rubric scores — placeholder scoring until DOM/screenshot wired."""
	findings: list[ReviewFinding] = []
	notes = [
		'uicrit_stage_1:contextualize',
		'uicrit_stage_2:generate_critiques',
		'uicrit_stage_3:score_rubric',
		'uicrit_stage_4:aggregate_overall',
	]
	degraded = ['uicrit_methodology_heuristic']

	insights = request.visual_insights or {}
	for issue in (insights.get('issues') or [])[:8]:
		kind = str(issue.get('kind', 'unknown'))
		category = _map_kind_to_uicrit_category(kind)
		findings.append(
			ReviewFinding(
				id=f'uicrit_{kind}_{len(findings)}',
				category=category,
				severity=str(issue.get('severity', 'advisory')),
				message=str(issue.get('detail', kind)),
				rationale='UICrit critique category mapping from visual inspection',
				source='uicrit',
			)
		)

	if request.region and request.region.selector:
		findings.append(
			ReviewFinding(
				id='uicrit_region_scope',
				category='layout',
				severity='advisory',
				message=f'Region-scoped critique requested: {request.region.label or request.region.selector}',
				rationale='UICrit supports targeted feedback for regions of interest',
				source='uicrit',
				selector=request.region.selector,
				region=request.region,
			)
		)

	scores = _heuristic_scores(request, findings)

	return {
		'findings': findings,
		'scores': scores,
		'notes': notes,
		'degraded': degraded,
	}


def _map_kind_to_uicrit_category(kind: str) -> str:
	lower = kind.lower()
	if 'contrast' in lower or 'color' in lower:
		return 'color_contrast'
	if 'truncat' in lower or 'text' in lower:
		return 'text_readability'
	if 'click' in lower or 'button' in lower:
		return 'button_usability'
	if 'overflow' in lower or 'layout' in lower:
		return 'layout'
	return 'learnability'


def _heuristic_scores(request: ReviewRequest, findings: list[ReviewFinding]) -> list[DimensionScore]:
	blocking = sum(1 for f in findings if f.severity == 'blocking')
	major = sum(1 for f in findings if f.severity == 'major')
	penalty = blocking * 2.0 + major * 1.0

	aesthetics = max(1.0, 8.0 - penalty)
	learnability = max(1.0, 4.0 - min(3.0, penalty))
	efficiency = max(1.0, 4.0 - min(2.0, penalty * 0.5))
	overall = max(1.0, 8.0 - penalty * 1.2)

	if not request.dom_snapshot and not request.visual_insights:
		notes = 'Scores are placeholder until DOM/screenshot inputs provided'
	else:
		notes = 'Heuristic scores from available inspection signals'

	return [
		DimensionScore('aesthetics', round(aesthetics, 1), 'scale_10', notes),
		DimensionScore('learnability', round(learnability, 1), 'likert_5', notes),
		DimensionScore('efficiency', round(efficiency, 1), 'likert_5', notes),
		DimensionScore('overall', round(overall, 1), 'scale_10', notes),
	]
