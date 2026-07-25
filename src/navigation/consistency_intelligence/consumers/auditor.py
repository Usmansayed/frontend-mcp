"""Batch consistency auditor — composes validator over snapshot observations."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.consumers.snapshot_observations import observations_from_snapshot
from navigation.consistency_intelligence.consumers.validator import ConsistencyValidator
from navigation.consistency_intelligence.knowledge.envelope import KnowledgeResponse
from navigation.consistency_intelligence.models import ConsistencyFinding, ConsistencyReport


def group_findings(findings: list[ConsistencyFinding]) -> list[dict[str, Any]]:
	"""Lint consolidation — group sub-violations by standard + property."""
	groups: dict[tuple[str, str], dict[str, Any]] = {}
	for f in findings:
		prop = str(f.metadata.get('property', ''))
		std_id = f.rule_id or 'unknown'
		key = (std_id, prop)
		entry = groups.get(key)
		if entry is None:
			entry = {
				'standard_id': std_id,
				'property': prop,
				'count': 0,
				'selectors': [],
				'expected': f.metadata.get('expected'),
				'severity': f.severity,
				'message': f.message,
			}
			groups[key] = entry
		entry['count'] += 1
		selector = f.metadata.get('selector') or f.id
		if selector and len(entry['selectors']) < 12:
			entry['selectors'].append(str(selector))
	return list(groups.values())


class ConsistencyAuditor:
	"""Batch audit consumer — queries graph via validator only."""

	def __init__(self, validator: ConsistencyValidator) -> None:
		self._validator = validator

	def audit_snapshot(
		self,
		snapshot: Any,
		*,
		project_id: str = 'default',
		max_elements: int = 40,
	) -> tuple[ConsistencyReport, list[KnowledgeResponse]]:
		observations = observations_from_snapshot(snapshot)[:max_elements]
		findings: list[ConsistencyFinding] = []
		responses: list[KnowledgeResponse] = []
		degraded: list[str] = []

		if not observations:
			degraded.append('audit_no_observations_in_snapshot')

		for obs in observations:
			assess, explain = self._validator.assess_with_explanation(
				selector=obs['selector'],
				actual=obs['actual'],
				context=obs.get('context'),
				project_id=project_id,
			)
			responses.append(assess)
			if explain:
				responses.append(explain)
			report = self._validator.to_report(assess, explain)
			for f in report.findings:
				f.metadata['selector'] = obs['selector']
				findings.append(f)
			degraded.extend(report.degraded)

		grouped = group_findings(findings)
		# Fail closed: stubs produce zero findings but must not pass.
		usable_assessments = [
			r for r in responses if getattr(r, 'answer', None) is not None
		]
		stub_or_unusable = any(
			(
				(getattr(r, 'answer', {}) or {}).get('status') == 'stub'
				or float(getattr(r, 'confidence', 0) or 0) <= 0
				or any(
					d in (getattr(r, 'degraded', None) or [])
					for d in ('knowledge_query_stub_phase1', 'discovery_pipeline_phase2')
				)
			)
			and not (getattr(r, 'answer', {}) or {}).get('skipped')
			and 'observation_no_matching_standard' not in (getattr(r, 'degraded', None) or [])
			for r in usable_assessments
		)
		# Skipped observations (no overlapping standards) are not findings and not stubs.
		assessed = [
			r for r in usable_assessments
			if not (getattr(r, 'answer', {}) or {}).get('skipped')
			and 'observation_no_matching_standard' not in (getattr(r, 'degraded', None) or [])
		]
		passed = bool(assessed) and len(findings) == 0 and not stub_or_unusable
		if stub_or_unusable and len(findings) == 0:
			summary = (
				f'Audit incomplete — {len(observations)} element(s) hit stub/empty standards '
				'(run Discovery; do not treat as pass).'
			)
		elif not assessed and observations:
			summary = (
				f'Audit skipped overlap — {len(observations)} element(s) had no matching '
				'foundation standards (graph populated but contexts did not overlap).'
			)
			# Not a false-green pass, not a Phase-1 stub.
			passed = False
			if 'audit_no_overlapping_standards' not in degraded:
				degraded.append('audit_no_overlapping_standards')
		elif passed:
			summary = f'Audit passed — {len(assessed)} element(s) match project standards.'
		else:
			summary = f'Audit found {len(findings)} deviation(s) across {len(grouped)} grouped issue(s).'
		report = ConsistencyReport(
			passed=passed,
			summary=summary,
			findings=findings,
			degraded=list(dict.fromkeys(degraded)),
		)
		report.findings  # noqa: B018 — attach grouped via metadata on report
		return report, responses

	def audit_report_with_groups(
		self,
		snapshot: Any,
		*,
		project_id: str = 'default',
		max_elements: int = 40,
	) -> dict[str, Any]:
		report, responses = self.audit_snapshot(snapshot, project_id=project_id, max_elements=max_elements)
		return {
			'passed': report.passed,
			'summary': report.summary,
			'findings': [f.to_dict() for f in report.findings],
			'grouped_findings': group_findings(report.findings),
			'elements_audited': min(len(observations_from_snapshot(snapshot)), max_elements),
			'degraded': report.degraded,
			'assessments': len(responses),
		}
