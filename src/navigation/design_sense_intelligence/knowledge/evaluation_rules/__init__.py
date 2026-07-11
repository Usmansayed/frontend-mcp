"""Evaluation rules, severity model, and domain checklists — from epistemology research."""
from __future__ import annotations

from ...models import FindingSeverity, ReviewFinding, ReviewRequest
from ..epistemology import DOMAIN_CHECKLISTS, RULE_HIERARCHY, SEVERITY_LEVELS
from ..types import EvaluationChecklist, SeverityLevel

__all__ = [
	'DOMAIN_CHECKLISTS',
	'RULE_HIERARCHY',
	'SEVERITY_LEVELS',
	'EvaluationChecklist',
	'SeverityLevel',
	'evaluate_against_rules',
	'severity_for_blocking_count',
]


def evaluate_against_rules(request: ReviewRequest) -> list[ReviewFinding]:
	"""Emit advisory findings only when snapshot lacks objective coverage for a domain."""
	from ...snapshot_access import resolve_snapshot

	snapshot = resolve_snapshot(request)
	if snapshot is not None:
		return _task_pattern_notes(request, snapshot)

	findings: list[ReviewFinding] = []
	task = (request.user_task or '').lower()

	for checklist in DOMAIN_CHECKLISTS:
		if not _checklist_applies(checklist, request, task):
			continue
		for i, item in enumerate(checklist.items[:3]):
			findings.append(
				ReviewFinding(
					id=f'checklist_{checklist.domain}_{i}',
					category=checklist.domain,
					severity=FindingSeverity.ADVISORY.value,
					message=f'Verify: {item}',
					rationale=f'{checklist.domain} AI verification checklist',
					recommendation=item,
					source='design_knowledge',
					confirmed=False,
					confidence=0.4,
					metadata={'lane': checklist.lane, 'checklist': checklist.domain},
				)
			)
	return findings


def _task_pattern_notes(request: ReviewRequest, snapshot) -> list[ReviewFinding]:
	"""Pattern hints suppressed when snapshot provides objective coverage."""
	return []


def severity_for_blocking_count(blocking: int, major: int) -> int:
	"""Map issue counts to Nielsen-style severity level (0–4)."""
	if blocking > 0:
		return 4
	if major >= 3:
		return 3
	if major > 0:
		return 2
	return 0


def _checklist_applies(checklist: EvaluationChecklist, request: ReviewRequest, task: str) -> bool:
	domain = checklist.domain
	if domain == 'typography' and ('text' in task or 'read' in task):
		return True
	if domain == 'layout' and request.scope in ('page', 'feature', 'component'):
		return True
	if domain == 'color' and request.computed_styles:
		return True
	if domain == 'navigation' and ('nav' in task or request.scope == 'flow'):
		return True
	if domain == 'interaction' and ('form' in task or 'click' in task or request.scope == 'flow'):
		return True
	if domain == 'layout':
		return True
	return False
