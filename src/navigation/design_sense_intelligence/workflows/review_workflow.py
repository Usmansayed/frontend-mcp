"""Microsoft-inspired review workflow phases."""
from __future__ import annotations

from ..models import QualityPillar, ReviewRequest

MICROSOFT_REVIEW_PHASES = [
	'identify_user_task',
	'check_design_system_patterns',
	'evaluate_aesthetic_direction',
	'identify_scope',
	'evaluate_quality_pillars',
	'score_and_prioritize',
	'recommend_with_examples',
]

PILLAR_DEFINITIONS = {
	QualityPillar.FRICTIONLESS.value: [
		'Task completable in ≤3 interactions?',
		'Primary action obvious and singular?',
		'Navigation clear and predictable?',
	],
	QualityPillar.CRAFT.value: [
		'Design system compliance (tokens, not hardcoded values)?',
		'Distinctive typography and cohesive color?',
		'Accessibility target WCAG 2.1 AA?',
	],
	QualityPillar.TRUSTWORTHY.value: [
		'AI/automation transparency where applicable?',
		'Actionable error messages?',
		'Exceptions documented with rationale?',
	],
}


def build_pillar_checklist(request: ReviewRequest) -> list[dict]:
	"""Heuristic checklist items — placeholders until browser/DOM inputs are wired."""
	items: list[dict] = []
	insights = request.visual_insights or {}
	blocking = insights.get('blocking') or []

	if blocking:
		items.append(
			{
				'id': 'ms_blocking_visual',
				'category': 'layout',
				'severity': 'blocking',
				'message': f'Blocking visual issues detected: {blocking[:2]}',
				'rationale': 'Quality Craft — layout/rendering blockers undermine trust',
				'recommendation': 'Resolve blocking visual issues before polish review',
				'pillar': QualityPillar.CRAFT.value,
				'flag': True,
			}
		)

	return items
