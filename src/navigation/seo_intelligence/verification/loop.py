"""Verification loop — metric-based re-measurement (ADR-027)."""
from __future__ import annotations

from navigation.seo_intelligence.models import (
	SeoAuditRequest,
	SeoAuditResult,
	SeoEvidenceRef,
	SeoRecommendation,
	SeoVerificationStatus,
)

_INDEX_PASS = frozenset({'PASS', 'NEUTRAL'})
_INDEX_FAIL = frozenset({'FAIL', 'PARTIAL'})


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
	"""Compare baseline vs current audit using stable evidence IDs and metric deltas."""
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

		status, notes = _judge_recommendation(rec, related_baseline=related_baseline, related_current=related_current)
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
			'metric_checks': _metric_checks(related_baseline, related_current),
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
	related_baseline: list[SeoEvidenceRef],
	related_current: list[SeoEvidenceRef],
) -> tuple[SeoVerificationStatus, str]:
	if not related_baseline:
		return SeoVerificationStatus.SKIPPED, 'no_baseline_evidence_for_recommendation'

	current_by_id = {e.evidence_id: e for e in related_current}
	improved = 0
	worsened = 0
	unchanged = 0
	missing = 0

	for base in related_baseline:
		curr = current_by_id.get(base.evidence_id)
		if curr is None:
			missing += 1
			if _issue_resolved_without_evidence(base):
				improved += 1
			continue
		outcome = _compare_evidence_metrics(base, curr)
		if outcome == 'improved':
			improved += 1
		elif outcome == 'worsened':
			worsened += 1
		else:
			unchanged += 1

	if worsened > 0:
		return SeoVerificationStatus.FAILED, 'metric_worsened'
	if improved > 0 and worsened == 0 and unchanged == 0:
		return SeoVerificationStatus.PASSED, 'all_related_metrics_improved_or_resolved'
	if improved > 0 and worsened == 0:
		return SeoVerificationStatus.PASSED, 'metrics_improved'
	if missing == len(related_baseline) and improved == len(related_baseline):
		return SeoVerificationStatus.PASSED, 'issues_no_longer_detected'

	baseline_high = sum(1 for e in related_baseline if e.severity in {'high', 'critical'})
	current_high = sum(1 for e in related_current if e.severity in {'high', 'critical'})
	if current_high < baseline_high:
		return SeoVerificationStatus.PASSED, 'severity_reduced'

	if unchanged > 0 and improved == 0:
		return SeoVerificationStatus.FAILED, 'issue_still_present:re_observe_and_fix'

	return SeoVerificationStatus.FAILED, 'verification_inconclusive'


_AI_STATUS_RANK = {'skipped': 0, 'fail': 1, 'warn': 2, 'pass': 3}


def _compare_evidence_metrics(baseline: SeoEvidenceRef, current: SeoEvidenceRef) -> str:
	kind = baseline.kind.value

	if kind == 'ai_visibility':
		before_status = str((baseline.metadata or {}).get('status') or '')
		after_status = str((current.metadata or {}).get('status') or '')
		before_rank = _AI_STATUS_RANK.get(before_status, 0)
		after_rank = _AI_STATUS_RANK.get(after_status, 0)
		if after_rank > before_rank:
			return 'improved'
		if after_rank < before_rank:
			return 'worsened'
		before_score = float((baseline.metadata or {}).get('score') or 0.0)
		after_score = float((current.metadata or {}).get('score') or 0.0)
		if after_score > before_score + 0.05:
			return 'improved'
		if after_score < before_score - 0.05:
			return 'worsened'
		return 'unchanged'

	if kind == 'index_status':
		before = str(baseline.metadata.get('verdict') or '')
		after = str(current.metadata.get('verdict') or '')
		if before in _INDEX_FAIL and after in _INDEX_PASS:
			return 'improved'
		if before in _INDEX_PASS and after in _INDEX_FAIL:
			return 'worsened'
		return 'unchanged'

	if kind == 'core_web_vital' and baseline.metric_value is not None and current.metric_value is not None:
		audit_id = str(baseline.metadata.get('auditId') or '')
		lower_is_better = 'cls' not in audit_id.lower() and baseline.metric_unit != 'score'
		if lower_is_better:
			if current.metric_value < baseline.metric_value:
				return 'improved'
			if current.metric_value > baseline.metric_value:
				return 'worsened'
		else:
			if current.metric_value < baseline.metric_value:
				return 'improved'
			if current.metric_value > baseline.metric_value:
				return 'worsened'

	if baseline.metric_unit == 'status_code' and baseline.metric_value is not None and current.metric_value is not None:
		if baseline.metric_value >= 400 and current.metric_value < 400:
			return 'improved'
		if current.metric_value >= 400 and baseline.metric_value < 400:
			return 'worsened'

	severity_rank = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}
	if severity_rank.get(current.severity, 0) < severity_rank.get(baseline.severity, 0):
		return 'improved'
	if severity_rank.get(current.severity, 0) > severity_rank.get(baseline.severity, 0):
		return 'worsened'

	return 'unchanged'


def _issue_resolved_without_evidence(baseline: SeoEvidenceRef) -> bool:
	"""Stable ID absent — only pass if issue type unlikely to recur without fix (conservative)."""
	return baseline.severity in {'high', 'critical'} and baseline.kind.value in {'technical_issue', 'crawl_issue'}


def _metric_checks(
	baseline: list[SeoEvidenceRef],
	current: list[SeoEvidenceRef],
) -> list[dict[str, object]]:
	current_by_id = {e.evidence_id: e for e in current}
	checks: list[dict[str, object]] = []
	for base in baseline:
		curr = current_by_id.get(base.evidence_id)
		checks.append({
			'evidence_id': base.evidence_id,
			'outcome': _compare_evidence_metrics(base, curr) if curr else 'missing',
			'baseline_metric': base.metric_value,
			'current_metric': curr.metric_value if curr else None,
		})
	return checks
