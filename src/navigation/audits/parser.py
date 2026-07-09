"""Parse Lighthouse LHR JSON into AuditReport."""
from __future__ import annotations

from typing import Any

from .models import AuditCategory, AuditIssue, AuditReport

_PERFORMANCE_METRIC_IDS = {
	'largest-contentful-paint': 'lcp_ms',
	'first-contentful-paint': 'fcp_ms',
	'speed-index': 'speed_index_ms',
	'interactive': 'tti_ms',
	'total-blocking-time': 'tbt_ms',
	'cumulative-layout-shift': 'cls',
}

_BLOCKING_SCORE_THRESHOLDS: dict[AuditCategory, float] = {
	AuditCategory.ACCESSIBILITY: 0.7,
	AuditCategory.PERFORMANCE: 0.5,
	AuditCategory.SEO: 0.8,
	AuditCategory.BEST_PRACTICES: 0.8,
}


def parse_lighthouse_report(lhr: dict[str, Any], category: AuditCategory) -> AuditReport:
	cat_key = category.value
	category_data = (lhr.get('categories') or {}).get(cat_key) or {}
	audits: dict[str, Any] = lhr.get('audits') or {}
	audit_refs = category_data.get('auditRefs') or []

	score_raw = category_data.get('score')
	score_pct = round(float(score_raw) * 100, 1) if score_raw is not None else 0.0

	failed = 0
	passed = 0
	manual = 0
	informative = 0
	not_applicable = 0
	issues: list[AuditIssue] = []

	for ref in audit_refs:
		audit_id = ref.get('id')
		if not audit_id:
			continue
		audit = audits.get(audit_id)
		if not audit:
			continue
		mode = str(audit.get('scoreDisplayMode') or '')
		audit_score = audit.get('score')

		if mode == 'manual':
			manual += 1
			continue
		if mode == 'informative':
			informative += 1
			continue
		if mode == 'notApplicable':
			not_applicable += 1
			continue
		if audit_score is None:
			continue
		if audit_score >= 0.9:
			passed += 1
			continue

		failed += 1
		impact = _impact_for_audit(float(audit_score), float(ref.get('weight') or 0))
		selector = _first_selector(audit)
		issues.append(
			AuditIssue(
				id=str(audit_id),
				title=str(audit.get('title') or audit_id),
				description=str(audit.get('description') or ''),
				score=float(audit_score) if audit_score is not None else None,
				impact=impact,
				selector=selector,
			)
		)

	issues.sort(key=lambda i: (_impact_rank(i.impact), -(i.score or 0)))
	warnings = [issue.to_dict() for issue in issues[:30]]

	blocking: list[str] = []
	threshold = _BLOCKING_SCORE_THRESHOLDS.get(category, 0.7)
	if score_raw is not None and float(score_raw) < threshold:
		blocking.append(f'{cat_key} score {score_pct} below threshold ({threshold * 100:.0f})')
	for issue in issues:
		if issue.impact in {'critical', 'serious'}:
			msg = f'{cat_key}: {issue.title}'
			if issue.selector:
				msg += f' ({issue.selector})'
			if msg not in blocking:
				blocking.append(msg)

	metrics = _extract_metrics(category, audits, lhr)

	return AuditReport(
		category=cat_key,
		url=str(lhr.get('finalDisplayedUrl') or lhr.get('requestedUrl') or ''),
		score=score_pct,
		blocking=blocking,
		warnings=warnings,
		metrics=metrics,
		audit_counts={
			'failed': failed,
			'passed': passed,
			'manual': manual,
			'informative': informative,
			'not_applicable': not_applicable,
		},
		lighthouse_version=str(lhr.get('lighthouseVersion') or ''),
	)


def _impact_rank(impact: str) -> int:
	return {'critical': 0, 'serious': 1, 'moderate': 2, 'minor': 3}.get(impact, 4)


def _impact_for_audit(score: float, weight: float) -> str:
	if score == 0:
		return 'critical' if weight >= 3 else 'serious'
	if score <= 0.5:
		return 'serious'
	if score <= 0.7:
		return 'moderate'
	return 'minor'


def _first_selector(audit: dict[str, Any]) -> str | None:
	details = audit.get('details') or {}
	items = details.get('items') if isinstance(details, dict) else None
	if not isinstance(items, list):
		return None
	for item in items:
		if not isinstance(item, dict):
			continue
		node = item.get('node')
		if isinstance(node, dict) and node.get('selector'):
			return str(node['selector'])
	return None


def _extract_metrics(category: AuditCategory, audits: dict[str, Any], lhr: dict[str, Any]) -> dict[str, Any]:
	if category != AuditCategory.PERFORMANCE:
		return {}

	metrics: dict[str, Any] = {}
	for audit_id, key in _PERFORMANCE_METRIC_IDS.items():
		audit = audits.get(audit_id) or {}
		if audit.get('numericValue') is not None:
			metrics[key] = audit['numericValue']
		elif audit.get('displayValue'):
			metrics[f'{key}_display'] = audit['displayValue']

	audits_ref = (lhr.get('categories') or {}).get('performance', {}).get('auditRefs') or []
	for ref in audits_ref:
		audit = audits.get(ref.get('id', '')) or {}
		if audit.get('scoreDisplayMode') == 'numeric' and audit.get('numericValue') is not None:
			metrics.setdefault(str(ref.get('id')), audit['numericValue'])
	return metrics
