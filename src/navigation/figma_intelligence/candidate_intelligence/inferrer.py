"""Infer candidate metadata from title, tags, and provider payload."""
from __future__ import annotations

import re

from navigation.figma_intelligence.models import CandidateProfile
from navigation.figma_intelligence.community_intelligence.lexicon import (
	COMPONENT_SYNONYMS,
	DESIGN_LANGUAGES,
	INDUSTRIES,
	PAGE_COMPONENT_EXPANSION,
	PAGE_SYNONYMS,
	STYLE_ALIASES,
	STYLE_MODIFIERS,
)

_COMPLEXITY_SIGNALS: dict[str, list[str]] = {
	'simple': ['minimal', 'clean', 'starter', 'basic'],
	'moderate': ['dashboard', 'kit', 'template', 'ui kit'],
	'complex': ['design system', 'full app', 'platform', 'enterprise', 'multi-page'],
}

_PATTERN_KEYWORDS: dict[str, list[str]] = {
	'bento_grid': ['bento', 'bento grid'],
	'glassmorphism': ['glass', 'glassmorphism', 'frosted'],
	'sidebar_layout': ['sidebar', 'side nav'],
	'data_dense': ['table', 'datagrid', 'analytics'],
	'marketing_hero': ['hero', 'landing'],
	'card_grid': ['card grid', 'feature grid'],
}


def infer_profile(
	*,
	title: str,
	tags: list[str],
	metadata: dict[str, object] | None = None,
) -> CandidateProfile:
	blob = _blob(title, tags, metadata)
	industry = _match_keys(blob, INDUSTRIES.keys())
	page_type = _match_page_types(blob)
	components = _match_components(blob, page_type)
	styles = [s for s in STYLE_MODIFIERS if s in blob]
	for raw, canonical in STYLE_ALIASES.items():
		if raw in blob and canonical not in styles:
			styles.append(canonical)
	design_language = [lang for lang in DESIGN_LANGUAGES if lang in blob]
	framework = _infer_framework(blob, metadata)
	complexity = _infer_complexity(blob)
	patterns = _infer_patterns(blob)
	confidence = _profile_confidence(industry, page_type, components, styles, framework)

	return CandidateProfile(
		industry=industry,
		page_type=page_type,
		components=components,
		framework=framework,
		style=styles,
		design_language=design_language,
		complexity=complexity,
		patterns=patterns,
		confidence=confidence,
	)


def _blob(title: str, tags: list[str], metadata: dict[str, object] | None) -> str:
	parts = [title.lower(), ' '.join(t.lower() for t in tags)]
	if metadata:
		for key in ('description', 'category', 'framework'):
			val = metadata.get(key)
			if isinstance(val, str):
				parts.append(val.lower())
	return ' '.join(parts)


def _match_keys(blob: str, keys: object) -> list[str]:
	return [k for k in keys if isinstance(k, str) and k in blob]


def _match_page_types(blob: str) -> list[str]:
	found = _match_keys(blob, PAGE_SYNONYMS.keys())
	for page, synonyms in PAGE_SYNONYMS.items():
		if any(s in blob for s in synonyms):
			if page not in found:
				found.append(page)
	return list(dict.fromkeys(found))


def _match_components(blob: str, page_types: list[str]) -> list[str]:
	found = _match_keys(blob, COMPONENT_SYNONYMS.keys())
	for page in page_types:
		found.extend(PAGE_COMPONENT_EXPANSION.get(page, [])[:4])
	for comp, synonyms in COMPONENT_SYNONYMS.items():
		if any(s in blob for s in synonyms) and comp not in found:
			found.append(comp)
	return list(dict.fromkeys(found))


def _infer_framework(blob: str, metadata: dict[str, object] | None) -> str | None:
	if metadata:
		fw = metadata.get('framework')
		if isinstance(fw, str) and fw.strip():
			return fw.strip()
	for token in ('react', 'next.js', 'nextjs', 'vue', 'tailwind', 'shadcn', 'figma'):
		if token in blob:
			return token
	return None


def _infer_complexity(blob: str) -> str:
	for level in ('complex', 'moderate', 'simple'):
		if any(sig in blob for sig in _COMPLEXITY_SIGNALS[level]):
			return level
	return 'unknown'


def _infer_patterns(blob: str) -> list[str]:
	found: list[str] = []
	for pattern, keywords in _PATTERN_KEYWORDS.items():
		if any(kw in blob for kw in keywords):
			found.append(pattern)
	return found


def _profile_confidence(
	industry: list[str],
	page_type: list[str],
	components: list[str],
	styles: list[str],
	framework: str | None,
) -> float:
	score = 0.2
	score += 0.15 if page_type else 0.0
	score += 0.15 if industry else 0.0
	score += 0.1 if components else 0.0
	score += 0.1 if styles else 0.0
	score += 0.1 if framework else 0.0
	return min(1.0, score)
