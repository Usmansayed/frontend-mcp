"""Attach the ``ai_readiness`` summary block to reasoning_context_v2.

Overall score is the mean of analyzer scores that ran (skipped analyzers do
not lower the score). Per-dimension entries are transparent — every score is
traceable back to a derived AI evidence item.
"""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.ai_visibility.analyzers.registry import registered_analyzer_ids
from navigation.seo_intelligence.models import SeoEvidenceRef

AI_READINESS_SCHEMA_VERSION = '1.0'


def attach_ai_readiness_block(
	ctx: dict[str, Any],
	*,
	evidence: list[SeoEvidenceRef],
) -> dict[str, Any]:
	ai_evidence = [e for e in evidence if e.kind.value == 'ai_visibility']
	if not ai_evidence:
		return ctx

	dimensions: dict[str, dict[str, Any]] = {}
	scored: list[float] = []
	for item in ai_evidence:
		analyzer_id = str((item.metadata or {}).get('analyzer_id') or '')
		if not analyzer_id:
			continue
		status = str((item.metadata or {}).get('status') or 'skipped')
		score = float((item.metadata or {}).get('score') or 0.0)
		if status != 'skipped':
			scored.append(score)
		dimensions[analyzer_id] = {
			'status': status,
			'score': score,
			'severity': item.severity,
			'title': item.title,
			'evidence_id': item.evidence_id,
			'source_evidence_ids': list((item.metadata or {}).get('source_evidence_ids') or []),
			'rationale_url': (item.metadata or {}).get('rationale_url'),
		}

	overall = round(sum(scored) / len(scored), 3) if scored else 0.0
	registered = registered_analyzer_ids()
	skipped_ids = [aid for aid in registered if aid not in dimensions]

	ctx['ai_readiness'] = {
		'schema_version': AI_READINESS_SCHEMA_VERSION,
		'overall_score': overall,
		'analyzers_run': len(dimensions) - sum(1 for d in dimensions.values() if d['status'] == 'skipped'),
		'analyzers_skipped': skipped_ids + [aid for aid, d in dimensions.items() if d['status'] == 'skipped'],
		'dimensions': dimensions,
		'sources_documented_in': 'src/navigation/seo_intelligence/ai_visibility/docs/ANALYZER_SOURCES.md',
	}
	return ctx
