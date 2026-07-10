"""Natural-language component query parser."""
from __future__ import annotations

import re

from ..models import ParsedQuery
from .lexicon import (
	ANIMATION_KEYWORDS,
	AUDIENCE_KEYWORDS,
	COMPONENT_TYPES,
	PAGE_CONTEXTS,
	PAGE_TYPES,
	STYLE_MODIFIERS,
	STYLE_ALIASES,
	THEME_KEYWORDS,
)


def parse_query(raw: str) -> ParsedQuery:
	text = ' '.join(raw.strip().lower().split())
	if not text:
		return ParsedQuery(raw=raw.strip())

	remaining = f' {text} '
	component_types: list[str] = []
	page_types: list[str] = []
	page_context: list[str] = []
	styles: list[str] = []
	animations: list[str] = []
	modifiers: list[str] = []
	audience: list[str] = []
	theme: str | None = None

	for phrase, value in sorted(THEME_KEYWORDS.items(), key=lambda item: -len(item[0])):
		token = f' {phrase} '
		if token in remaining:
			theme = value
			remaining = remaining.replace(token, ' ')
			modifiers.append(phrase)

	for phrase in sorted(PAGE_TYPES, key=len, reverse=True):
		token = f' {phrase} '
		if token in remaining:
			page_types.append(phrase)
			page_context.append(_page_context_from_phrase(phrase))
			remaining = remaining.replace(token, ' ')

	for phrase in sorted(PAGE_CONTEXTS, key=len, reverse=True):
		token = f' {phrase} '
		if token in remaining:
			page_context.append(phrase)
			if phrase in AUDIENCE_KEYWORDS:
				audience.append(phrase)
			remaining = remaining.replace(token, ' ')

	for word in sorted(COMPONENT_TYPES, key=len, reverse=True):
		token = f' {word} '
		if token in remaining:
			component_types.append(_normalize_component_type(word))
			remaining = remaining.replace(token, ' ')

	for phrase in sorted(STYLE_MODIFIERS, key=len, reverse=True):
		token = f' {phrase} '
		if token in remaining:
			canonical = STYLE_ALIASES.get(phrase, phrase)
			styles.append(canonical)
			remaining = remaining.replace(token, ' ')
			modifiers.append(phrase)

	for word in sorted(ANIMATION_KEYWORDS, key=len, reverse=True):
		token = f' {word} '
		if token in remaining:
			animations.append(word)
			remaining = remaining.replace(token, ' ')

	for word in sorted(AUDIENCE_KEYWORDS, key=len, reverse=True):
		token = f' {word} '
		if token in remaining:
			audience.append(word)
			page_context.append(word)
			remaining = remaining.replace(token, ' ')

	keywords = _tokenize(remaining)
	seen: set[str] = set()
	unique_keywords: list[str] = []
	for kw in keywords:
		if kw not in seen:
			seen.add(kw)
			unique_keywords.append(kw)

	search_hints = _build_search_hints(
		component_types=component_types,
		page_context=page_context,
		styles=styles,
		animations=animations,
		audience=audience,
		theme=theme,
	)

	return ParsedQuery(
		raw=raw.strip(),
		keywords=unique_keywords,
		component_types=component_types,
		page_types=page_types,
		page_context=_dedupe(page_context),
		styles=_dedupe(styles),
		animations=_dedupe(animations),
		theme=theme,
		modifiers=_dedupe(modifiers),
		audience=_dedupe(audience),
		search_hints=search_hints,
	)


def build_search_text(parsed: ParsedQuery) -> str:
	parts = [parsed.raw]
	parts.extend(parsed.component_types)
	parts.extend(parsed.page_types)
	parts.extend(parsed.page_context)
	parts.extend(parsed.styles)
	parts.extend(parsed.animations)
	parts.extend(parsed.modifiers)
	parts.extend(parsed.audience)
	parts.extend(parsed.search_hints)
	parts.extend(parsed.keywords)
	if parsed.theme:
		parts.append(parsed.theme)
	return ' '.join(p for p in parts if p).strip()


def _build_search_hints(
	*,
	component_types: list[str],
	page_context: list[str],
	styles: list[str],
	animations: list[str],
	audience: list[str],
	theme: str | None,
) -> list[str]:
	hints: list[str] = []
	hints.extend(component_types)
	hints.extend(page_context)
	hints.extend(styles)
	hints.extend(animations)
	hints.extend(audience)
	if theme:
		hints.append(theme)
	return _dedupe(hints)


def _normalize_component_type(word: str) -> str:
	if word in ('nav', 'navigation', 'header'):
		return 'navbar'
	return word


def _page_context_from_phrase(phrase: str) -> str:
	if 'login' in phrase or 'signup' in phrase or 'auth' in phrase:
		return 'auth'
	if 'dashboard' in phrase:
		return 'dashboard'
	if 'settings' in phrase:
		return 'settings'
	if 'landing' in phrase:
		return 'landing page'
	if 'pricing' in phrase:
		return 'marketing'
	return phrase


def _tokenize(text: str) -> list[str]:
	clean = re.sub(r'[^a-z0-9\-]+', ' ', text.lower())
	return [tok for tok in clean.split() if len(tok) > 1]


def _dedupe(items: list[str]) -> list[str]:
	seen: set[str] = set()
	out: list[str] = []
	for item in items:
		key = item.strip().lower()
		if key and key not in seen:
			seen.add(key)
			out.append(item.strip())
	return out
