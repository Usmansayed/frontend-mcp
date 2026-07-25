"""Analyzer contract and registry — must stay in sync with ANALYZER_SOURCES.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from navigation.seo_intelligence.models import SeoEvidenceRef


@dataclass(slots=True)
class AiAnalyzerResult:
	"""Result emitted by a single AI readiness analyzer.

	`status` values:
	- ``pass``    — signal is healthy (score >= 0.8)
	- ``warn``    — partial or minor gap
	- ``fail``    — required signal missing / broken
	- ``skipped`` — required upstream evidence not available; not counted in overall score
	"""

	analyzer_id: str
	status: str
	score: float
	source_evidence_ids: list[str] = field(default_factory=list)
	page_url: str = ''
	rationale: str = ''
	rationale_url: str = ''
	severity: str = 'info'
	title: str = ''
	summary: str = ''
	metadata: dict[str, Any] = field(default_factory=dict)


AiAnalyzer = Callable[[list[SeoEvidenceRef], str], AiAnalyzerResult]


def _lazy_registry() -> list[AiAnalyzer]:
	from navigation.seo_intelligence.ai_visibility.analyzers.citation_readiness import analyze as citation_readiness
	from navigation.seo_intelligence.ai_visibility.analyzers.content_structure import analyze as content_structure
	from navigation.seo_intelligence.ai_visibility.analyzers.crawlability import analyze as crawlability
	from navigation.seo_intelligence.ai_visibility.analyzers.crawler_access import analyze as crawler_access
	from navigation.seo_intelligence.ai_visibility.analyzers.entity_coverage import analyze as entity_coverage
	from navigation.seo_intelligence.ai_visibility.analyzers.extractability import analyze as extractability
	from navigation.seo_intelligence.ai_visibility.analyzers.faq_answer_blocks import analyze as faq_answer_blocks
	from navigation.seo_intelligence.ai_visibility.analyzers.internal_linking import analyze as internal_linking
	from navigation.seo_intelligence.ai_visibility.analyzers.llms_txt import analyze as llms_txt
	from navigation.seo_intelligence.ai_visibility.analyzers.schema_quality import analyze as schema_quality
	from navigation.seo_intelligence.ai_visibility.analyzers.semantic_html import analyze as semantic_html
	from navigation.seo_intelligence.ai_visibility.analyzers.trust_signals import analyze as trust_signals

	return [
		crawlability,
		crawler_access,
		extractability,
		citation_readiness,
		entity_coverage,
		schema_quality,
		semantic_html,
		faq_answer_blocks,
		trust_signals,
		internal_linking,
		content_structure,
		llms_txt,
	]


class _LazyList:
	"""Import analyzers on first access to avoid circular imports at module load."""

	def __init__(self) -> None:
		self._items: list[AiAnalyzer] | None = None

	def _resolve(self) -> list[AiAnalyzer]:
		if self._items is None:
			self._items = _lazy_registry()
		return self._items

	def __iter__(self):
		return iter(self._resolve())

	def __len__(self) -> int:
		return len(self._resolve())

	def __getitem__(self, index: int) -> AiAnalyzer:
		return self._resolve()[index]


ANALYZER_REGISTRY = _LazyList()


def registered_analyzer_ids() -> list[str]:
	"""Analyzer IDs in registration order (matches ANALYZER_SOURCES.md table)."""
	return [
		'ai_crawlability',
		'ai_crawler_access',
		'ai_extractability',
		'ai_citation_readiness',
		'ai_entity_coverage',
		'ai_schema_quality',
		'ai_semantic_html',
		'ai_faq_answer_blocks',
		'ai_trust_signals',
		'ai_internal_linking',
		'ai_content_structure',
		'ai_llms_txt_optional',
	]
