"""Normalize Lighthouse LHR JSON into SEO evidence."""
from __future__ import annotations

from typing import Any

from navigation.frontend_quality_intelligence.audits.models import AuditCategory
from navigation.frontend_quality_intelligence.audits.parser import parse_lighthouse_report
from navigation.seo_intelligence.evidence.identity import stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef

_CWV_AUDIT_IDS = {
	'largest-contentful-paint': ('LCP', 'ms', 2500.0, 4000.0),
	'cumulative-layout-shift': ('CLS', 'score', 0.1, 0.25),
	'interactive': ('INP proxy (TTI)', 'ms', 200.0, 500.0),
	'total-blocking-time': ('TBT', 'ms', 200.0, 600.0),
	'speed-index': ('Speed Index', 'ms', 3400.0, 5800.0),
}


def normalize_lighthouse_reports(
	*,
	performance_lhr: dict[str, Any] | None,
	seo_lhr: dict[str, Any] | None,
	provider_id: str = 'lighthouse',
) -> list[SeoEvidenceRef]:
	evidence: list[SeoEvidenceRef] = []
	if performance_lhr:
		evidence.extend(_normalize_performance(performance_lhr, provider_id=provider_id))
	if seo_lhr:
		evidence.extend(_normalize_seo(seo_lhr, provider_id=provider_id))
	return evidence


def _page_url_from_lhr(lhr: dict[str, Any]) -> str:
	return str(lhr.get('finalDisplayedUrl') or lhr.get('requestedUrl') or '')


def _normalize_performance(lhr: dict[str, Any], *, provider_id: str) -> list[SeoEvidenceRef]:
	report = parse_lighthouse_report(lhr, AuditCategory.PERFORMANCE)
	evidence: list[SeoEvidenceRef] = []
	page_url = _page_url_from_lhr(lhr)
	audits = lhr.get('audits') or {}
	for audit_id, (label, unit, good, poor) in _CWV_AUDIT_IDS.items():
		audit = audits.get(audit_id) or {}
		value = audit.get('numericValue')
		if value is None:
			continue
		value_f = float(value)
		severity = 'info'
		if unit == 'score':
			if value_f > poor:
				severity = 'high'
			elif value_f > good:
				severity = 'medium'
		elif value_f > poor:
			severity = 'high'
		elif value_f > good:
			severity = 'medium'
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.CORE_WEB_VITAL.value,
					page_url=page_url,
					source_ref=f'lighthouse.audit.{audit_id}',
					metric_key=audit_id,
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.CORE_WEB_VITAL,
				title=f'{label}: {audit.get("displayValue") or value_f}',
				summary=str(audit.get('description') or f'{label} measured at {value_f}'),
				url=page_url,
				page_url=page_url,
				metric_value=value_f,
				metric_unit=unit,
				severity=severity,
				source_ref=f'lighthouse.audit.{audit_id}',
				metadata={'auditId': audit_id, 'score': audit.get('score')},
			)
		)

	if report.score < 50:
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.PERFORMANCE.value,
					page_url=page_url,
					source_ref='lighthouse.performance',
					metric_key='score',
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.PERFORMANCE,
				title=f'Lighthouse performance score {report.score}',
				summary='; '.join(report.blocking[:3]) if report.blocking else 'Low performance score',
				url=page_url,
				page_url=page_url,
				metric_value=report.score,
				metric_unit='score',
				severity='high',
				source_ref='lighthouse.performance',
				metadata={'blocking': report.blocking},
			)
		)
	return evidence


def _normalize_seo(lhr: dict[str, Any], *, provider_id: str) -> list[SeoEvidenceRef]:
	report = parse_lighthouse_report(lhr, AuditCategory.SEO)
	evidence: list[SeoEvidenceRef] = []
	page_url = _page_url_from_lhr(lhr) or report.url
	for index, issue in enumerate(report.warnings[:20]):
		impact = issue.get('impact') or 'moderate'
		severity = 'high' if impact in {'critical', 'serious'} else 'medium'
		issue_id = str(issue.get('id') or index)
		title = str(issue.get('title') or 'SEO audit issue')
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.TECHNICAL_ISSUE.value,
					page_url=page_url,
					title=title,
					source_ref='lighthouse.seo',
					metric_key=issue_id,
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.TECHNICAL_ISSUE,
				title=title,
				summary=str(issue.get('description') or ''),
				url=page_url,
				page_url=page_url,
				severity=severity,
				source_ref='lighthouse.seo',
				metadata=dict(issue),
			)
		)
	if report.score < 80:
		evidence.append(
			SeoEvidenceRef(
				evidence_id=stable_evidence_id(
					provider_id,
					SeoEvidenceKind.TECHNICAL_ISSUE.value,
					page_url=page_url,
					source_ref='lighthouse.seo.score',
					metric_key='score',
				),
				provider_id=provider_id,
				kind=SeoEvidenceKind.TECHNICAL_ISSUE,
				title=f'Lighthouse SEO score {report.score}',
				summary='; '.join(report.blocking[:3]) if report.blocking else 'SEO score below threshold',
				url=page_url,
				page_url=page_url,
				metric_value=report.score,
				metric_unit='score',
				severity='medium' if report.score >= 50 else 'high',
				source_ref='lighthouse.seo.score',
			)
		)
	return evidence
