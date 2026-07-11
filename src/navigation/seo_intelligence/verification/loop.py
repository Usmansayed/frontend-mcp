"""Verification loop — analyze → recommend → apply → verify → repeat."""
from __future__ import annotations

from navigation.seo_intelligence.models import (
	SeoAuditRequest,
	SeoAuditResult,
	SeoRecommendation,
	SeoVerificationStatus,
)


def build_verification_plan(recommendations: list[SeoRecommendation]) -> dict[str, object]:
	steps = []
	for rec in recommendations:
		steps.append({
			'recommendation_id': rec.recommendation_id,
			'status': SeoVerificationStatus.PENDING.value,
			'steps': list(rec.verification_steps) or [
				'Apply recommended fix in codebase',
				'perception_observe affected URL',
				'perception_verify expected outcome',
				'perception_seo_verify',
			],
		})
	return {
		'loop': 'analyze_recommend_apply_verify_repeat',
		'pending_count': len(steps),
		'items': steps,
	}


def evaluate_verification(
	*,
	baseline: SeoAuditResult,
	current: SeoAuditResult,
	recommendation_ids: list[str],
) -> dict[str, object]:
	"""Compare baseline vs current audit to close verification items."""
	baseline_evidence = {e.evidence_id: e for e in baseline.evidence}
	current_evidence = {e.evidence_id: e for e in current.evidence}
	rec_by_id = {r.recommendation_id: r for r in baseline.recommendations}

	target_ids = recommendation_ids or [r.recommendation_id for r in baseline.recommendations]
	items: list[dict[str, object]] = []
	passed = 0
	failed = 0
	skipped = 0

	for rec_id in target_ids:
		rec = rec_by_id.get(rec_id)
		if rec is None:
			skipped += 1
			items.append({
				'recommendation_id': rec_id,
				'status': SeoVerificationStatus.SKIPPED.value,
				'notes': 'recommendation_not_found_in_baseline',
			})
			continue

		related_baseline = [baseline_evidence[eid] for eid in rec.evidence_ids if eid in baseline_evidence]
		related_current = [current_evidence[eid] for eid in rec.evidence_ids if eid in current_evidence]

		status, notes = _judge_recommendation(
			rec,
			related_baseline=related_baseline,
			related_current=related_current,
			baseline_count=len(baseline.evidence),
			current_count=len(current.evidence),
		)
		if status == SeoVerificationStatus.PASSED:
			passed += 1
		elif status == SeoVerificationStatus.FAILED:
			failed += 1
		else:
			skipped += 1
		items.append({
			'recommendation_id': rec_id,
			'status': status.value,
			'notes': notes,
			'evidence_ids': list(rec.evidence_ids),
		})

	return {
		'loop': 'analyze_recommend_apply_verify_repeat',
		'passed_count': passed,
		'failed_count': failed,
		'skipped_count': skipped,
		'items': items,
	}


def _judge_recommendation(
	rec: SeoRecommendation,
	*,
	related_baseline: list,
	related_current: list,
	baseline_count: int,
	current_count: int,
) -> tuple[SeoVerificationStatus, str]:
	if not related_baseline:
		return SeoVerificationStatus.SKIPPED, 'no_baseline_evidence_for_recommendation'

	if not related_current:
		return SeoVerificationStatus.PASSED, 'related_evidence_no_longer_present'

	baseline_high = sum(1 for e in related_baseline if e.severity in {'high', 'critical'})
	current_high = sum(1 for e in related_current if e.severity in {'high', 'critical'})

	if current_high < baseline_high:
		return SeoVerificationStatus.PASSED, 'high_severity_evidence_reduced'

	if current_count < baseline_count and rec.category == 'cross_analysis':
		return SeoVerificationStatus.PASSED, 'overall_evidence_improved'

	if current_high > baseline_high:
		return SeoVerificationStatus.FAILED, 'high_severity_evidence_increased'

	return SeoVerificationStatus.FAILED, 'issue_still_present:re_observe_and_fix'
