"""Shared analyzer helpers."""
from __future__ import annotations

from navigation.seo_intelligence.evidence.identity import normalize_page_url
from navigation.seo_intelligence.models import SeoEvidenceRef

_AI_GUIDE_URL = 'https://developers.google.com/search/docs/fundamentals/ai-optimization-guide'


def ai_guide_url() -> str:
	return _AI_GUIDE_URL


def evidence_by_kind(evidence: list[SeoEvidenceRef], kinds: set[str]) -> list[SeoEvidenceRef]:
	return [e for e in evidence if e.kind.value in kinds]


def has_any(evidence: list[SeoEvidenceRef], kinds: set[str]) -> bool:
	return any(e.kind.value in kinds for e in evidence)


def normalized_metadata_text(item: SeoEvidenceRef) -> str:
	parts: list[str] = [item.title or '', item.summary or '']
	for value in (item.metadata or {}).values():
		if isinstance(value, str):
			parts.append(value)
	return ' '.join(parts).lower()


def matches_any_phrase(item: SeoEvidenceRef, phrases: tuple[str, ...]) -> bool:
	text = normalized_metadata_text(item)
	return any(phrase in text for phrase in phrases)


def primary_page_url(evidence: list[SeoEvidenceRef], base_url: str) -> str:
	for item in evidence:
		page = item.page_url or item.url
		if page and page.startswith('http'):
			return normalize_page_url(page, base_url=base_url)
	return normalize_page_url(base_url) if base_url else ''
