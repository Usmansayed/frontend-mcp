"""AI Visibility Adapter — derives ai_visibility evidence from collected SEO evidence.

The adapter never fetches data. It reads the already-collected `SeoEvidenceRef`
list from GSC, LibreCrawl, Lighthouse and Browser, runs analyzers documented
in ``docs/ANALYZER_SOURCES.md``, and returns a new list of
``SeoEvidenceKind.AI_VISIBILITY`` refs plus degraded notes for analyzers that
lacked upstream evidence.
"""
from __future__ import annotations

from navigation.seo_intelligence.ai_visibility.analyzers import ANALYZER_REGISTRY
from navigation.seo_intelligence.ai_visibility.normalize import analyzer_result_to_evidence
from navigation.seo_intelligence.models import SeoEvidenceRef


class AiVisibilityAdapter:
	"""Runs analyzers against collected SEO evidence and returns derived evidence."""

	def derive(
		self,
		evidence: list[SeoEvidenceRef],
		*,
		base_url: str = '',
	) -> tuple[list[SeoEvidenceRef], list[str]]:
		derived: list[SeoEvidenceRef] = []
		degraded: list[str] = []
		for analyzer in ANALYZER_REGISTRY:
			try:
				result = analyzer(evidence, base_url)
			except Exception as exc:
				degraded.append(f'ai_readiness_analyzer_error:{analyzer.__module__}:{type(exc).__name__}')
				continue
			if result.status == 'skipped':
				degraded.append(f'ai_readiness_insufficient_evidence:{result.analyzer_id}')
				continue
			derived.append(analyzer_result_to_evidence(result, base_url=base_url))
		return derived, degraded
