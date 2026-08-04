"""Frozen public contract — reasoning_context_v2 (ADR-027).

Everything downstream (deterministic fallback, AI reasoning, verification) consumes
this structure. No module bypasses it.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.knowledge.graph.pages import group_evidence_by_page, page_entity_from_evidence
from navigation.seo_intelligence.models import SeoAuditMode, SeoEvidenceRef
from navigation.seo_intelligence.reasoning.confidence import compose_confidence

REASONING_CONTEXT_V2_VERSION = '2.0'


def build_reasoning_context_v2(
	*,
	audit_id: str,
	evidence: list[SeoEvidenceRef],
	correlations: list[dict[str, Any]],
	mode: SeoAuditMode,
	website_url: str,
	providers: dict[str, str],
	graph_summary: dict[str, Any] | None = None,
	verification_history: dict[str, Any] | None = None,
	snapshot_diff: dict[str, Any] | None = None,
	previous_audit_id: str = '',
	collected_at: float | None = None,
) -> dict[str, Any]:
	collected_at = collected_at or time.time()
	base_url = website_url.strip()
	pages_by_key = group_evidence_by_page(evidence, base_url=base_url)

	pages: list[dict[str, Any]] = []
	for page_key, items in sorted(pages_by_key.items()):
		entity = page_entity_from_evidence(page_key, items, base_url=base_url)
		page_correlations = [
			c for c in correlations
			if c.get('page_url') == entity['url'] or (not c.get('page_url') and page_key == '__site__')
		]
		entity['correlations'] = page_correlations
		entity['confidence'] = compose_confidence(
			items,
			collected_at=collected_at,
		)
		entity['codebase_hints'] = []
		pages.append(entity)

	site_correlations = [c for c in correlations if c.get('scope') == 'site']
	reasoning_units = _build_reasoning_units(
		correlations,
		evidence,
		pages,
		collected_at=collected_at,
	)

	return {
		'schema_version': REASONING_CONTEXT_V2_VERSION,
		'meta': {
			'audit_id': audit_id,
			'snapshot_id': audit_id,
			'previous_audit_id': previous_audit_id or None,
			'mode': mode.value,
			'collected_at': collected_at,
			'website_url': base_url,
		},
		'providers': dict(providers),
		'pages': pages,
		'site_correlations': site_correlations,
		'reasoning_units': reasoning_units,
		'snapshot_diff': snapshot_diff,
		'verification_state': dict(verification_history or {}),
		'knowledge_graph': dict(graph_summary or {}),
		'evidence_count': len(evidence),
		'constraints': {
			'must_cite_evidence_ids': True,
			'must_not_invent_metrics': True,
			'ai_consumes_this_only': True,
		},
	}


def new_audit_id() -> str:
	return f'audit_{uuid.uuid4().hex[:16]}'


def _build_reasoning_units(
	correlations: list[dict[str, Any]],
	evidence: list[SeoEvidenceRef],
	pages: list[dict[str, Any]],
	*,
	collected_at: float,
) -> list[dict[str, Any]]:
	evidence_by_id = {e.evidence_id: e for e in evidence}
	units: list[dict[str, Any]] = []

	for corr in correlations:
		evidence_ids = [str(eid) for eid in (corr.get('evidence_ids') or []) if eid]
		if not evidence_ids:
			continue
		related = [evidence_by_id[eid] for eid in evidence_ids if eid in evidence_by_id]
		page_url = str(corr.get('page_url') or '')
		if not page_url and related:
			from navigation.seo_intelligence.evidence.identity import page_url_for_evidence

			page_url = page_url_for_evidence(related[0])

		analysis_id = str(corr.get('analysis_id') or corr.get('correlation_id') or 'hypothesis')
		unit_id = f'ru:{normalize_page_url(page_url) or "site"}:{analysis_id}'

		confidence = compose_confidence(
			related,
			providers_present=list(corr.get('providers') or []),
			collected_at=collected_at,
		)
		impact = score_impact(related, page_url=page_url)

		units.append({
			'unit_id': unit_id,
			'page_url': page_url,
			'kind': str(corr.get('category') or 'correlation_hypothesis'),
			'title': str(corr.get('title') or ''),
			'summary': str(corr.get('summary') or ''),
			'root_cause': str(corr.get('root_cause') or ''),
			'business_impact': str(corr.get('business_impact') or ''),
			'evidence_ids': evidence_ids,
			'correlation_id': analysis_id,
			'metrics': _metrics_for_unit(related, pages, page_url),
			'confidence': confidence,
			'impact': impact,
			'constraints': {
				'must_cite_evidence_ids': True,
				'must_not_invent_metrics': True,
			},
		})

	return units


def _metrics_for_unit(
	related: list[SeoEvidenceRef],
	pages: list[dict[str, Any]],
	page_url: str,
) -> dict[str, Any]:
	normalized = normalize_page_url(page_url)
	for page in pages:
		if page.get('url') == normalized or (not normalized and page.get('page_key') == '__site__'):
			return dict(page.get('metrics') or {})
	return {}


from navigation.seo_intelligence.reasoning.impact import score_impact
