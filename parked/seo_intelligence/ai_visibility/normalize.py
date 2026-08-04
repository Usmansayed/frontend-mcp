"""Convert analyzer results to SEO evidence refs — reuses stable ID helper."""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers.registry import AiAnalyzerResult
from navigation.seo_intelligence.evidence.identity import stable_evidence_id
from navigation.seo_intelligence.models import SeoEvidenceKind, SeoEvidenceRef

AI_PROVIDER_ID = 'ai-visibility'


def analyzer_result_to_evidence(
	result: AiAnalyzerResult,
	*,
	base_url: str = '',
) -> SeoEvidenceRef:
	source_ref = f'ai_visibility.{result.analyzer_id}'
	evidence_id = stable_evidence_id(
		AI_PROVIDER_ID,
		SeoEvidenceKind.AI_VISIBILITY.value,
		page_url=result.page_url,
		title=result.title or result.analyzer_id,
		source_ref=source_ref,
		metric_key=result.status,
		base_url=base_url,
	)
	metadata = dict(result.metadata)
	metadata.update({
		'analyzer_id': result.analyzer_id,
		'status': result.status,
		'score': result.score,
		'source_evidence_ids': list(result.source_evidence_ids),
		'rationale': result.rationale,
		'rationale_url': result.rationale_url,
	})
	return SeoEvidenceRef(
		evidence_id=evidence_id,
		provider_id=AI_PROVIDER_ID,
		kind=SeoEvidenceKind.AI_VISIBILITY,
		title=result.title or f'AI readiness: {result.analyzer_id}',
		summary=result.summary or result.rationale or result.analyzer_id,
		page_url=result.page_url,
		metric_value=result.score,
		metric_unit='score',
		severity=result.severity,
		source_ref=source_ref,
		metadata=metadata,
	)
