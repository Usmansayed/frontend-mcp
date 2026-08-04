"""Thin consistency validator — composes Knowledge API queries only."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.knowledge.api import KnowledgeAPI
from navigation.consistency_intelligence.knowledge.envelope import KnowledgeResponse
from navigation.consistency_intelligence.models import ConsistencyFinding, ConsistencyReport

_STUB_DEGRADED = frozenset(
	{
		'knowledge_query_stub_phase1',
		'discovery_pipeline_phase2',
	}
)


def _assess_usable(assess: KnowledgeResponse) -> bool:
	"""Fail closed: stubs / zero-confidence / stub tags are not a pass."""
	if (assess.answer or {}).get('skipped'):
		return False
	if 'observation_no_matching_standard' in (assess.degraded or []):
		return False
	if assess.answer.get('status') == 'stub':
		return False
	if float(assess.confidence or 0.0) <= 0.0:
		return False
	if any(d in _STUB_DEGRADED for d in (assess.degraded or [])):
		return False
	return True


class ConsistencyValidator:
	"""Phase 3 consumer — never learns or stores design knowledge."""

	def __init__(self, api: KnowledgeAPI) -> None:
		self._api = api

	def assess(
		self,
		*,
		selector: str,
		actual: dict[str, str],
		context: str | None = None,
		properties: list[str] | None = None,
		project_id: str = 'default',
	) -> KnowledgeResponse:
		params: dict[str, Any] = {'selector': selector, 'actual': actual}
		if context:
			params['context'] = context
		if properties:
			params['properties'] = properties
		return self._api.query('consistency.assess', params, project_id=project_id)

	def explain(
		self,
		*,
		selector: str,
		actual: dict[str, str],
		context: str | None = None,
		properties: list[str] | None = None,
		project_id: str = 'default',
	) -> KnowledgeResponse:
		params: dict[str, Any] = {'selector': selector, 'actual': actual}
		if context:
			params['context'] = context
		if properties:
			params['properties'] = properties
		return self._api.query('consistency.explain', params, project_id=project_id)

	def assess_with_explanation(
		self,
		*,
		selector: str,
		actual: dict[str, str],
		context: str | None = None,
		properties: list[str] | None = None,
		project_id: str = 'default',
	) -> tuple[KnowledgeResponse, KnowledgeResponse | None]:
		"""Contract: assess first; explain only when inconsistent."""
		assess = self.assess(
			selector=selector,
			actual=actual,
			context=context,
			properties=properties,
			project_id=project_id,
		)
		if not _assess_usable(assess):
			return assess, None
		# Missing `consistent` must fail closed (not default True).
		if assess.answer.get('consistent', False):
			return assess, None
		explain = self.explain(
			selector=selector,
			actual=actual,
			context=context,
			properties=properties or [d['property'] for d in assess.answer.get('deviations', [])],
			project_id=project_id,
		)
		return assess, explain

	def to_report(
		self,
		assess: KnowledgeResponse,
		explain: KnowledgeResponse | None = None,
	) -> ConsistencyReport:
		"""Map KnowledgeResponse → legacy ConsistencyReport for MCP adapters."""
		usable = _assess_usable(assess)
		if not usable:
			consistent = False
			summary = (
				assess.answer.get('message')
				or 'Consistency assess stub / no usable standards — run Discovery and re-assess with exact context keys.'
			)
		else:
			consistent = bool(assess.answer.get('consistent', False))
			summary = (
				f'Consistent with project standards ({assess.confidence:.0%} confidence).'
				if consistent
				else None
			)
		findings: list[ConsistencyFinding] = []
		source = explain or assess
		for dev in source.answer.get('deviations') or []:
			findings.append(
				ConsistencyFinding(
					id=f"dev_{dev.get('standard_id', 'unknown')}_{dev.get('property', '')}",
					category='consistency',
					severity='minor' if (dev.get('confidence') or 0) < 0.9 else 'major',
					message=(
						f"{dev.get('property')}: actual `{dev.get('actual')}` "
						f"vs expected {dev.get('expected')}"
					),
					recommendation=(
						source.recommendation.detail if source.recommendation else 'Align to project standard'
					),
					rule_id=str(dev.get('standard_id', '')),
					metadata=dict(dev),
				)
			)
		if summary is None:
			summary = f'{len(findings)} deviation(s) from project standards.'
		degraded = list(dict.fromkeys([*assess.degraded, *(explain.degraded if explain else [])]))
		return ConsistencyReport(passed=consistent, summary=summary, findings=findings, degraded=degraded)
