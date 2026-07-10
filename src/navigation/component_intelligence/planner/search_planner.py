"""Deterministic search plan builder (host agent may override with LLM-generated plan)."""
from __future__ import annotations

from ..models import ParsedQuery, PlannedQuery, SearchPlan
from .provider_vocabulary import DEFAULT_REGISTRIES, STYLE_REGISTRY_AFFINITY
from .synonyms import BROAD_CONCEPTS, COMPONENT_SYNONYMS


def build_search_plan(parsed: ParsedQuery) -> SearchPlan:
	component_types = _unique(parsed.component_types + _infer_component_types(parsed))
	page_context = _unique(parsed.page_context + parsed.page_types)
	style_keywords = _unique(parsed.styles + parsed.modifiers)
	alt_terms = _expand_terminology(component_types)
	primary_intent = _primary_intent(parsed, component_types, page_context, style_keywords)
	planned_queries = _build_planned_queries(parsed, component_types, page_context, style_keywords, alt_terms)
	suggested_registries = _suggest_registries(parsed, component_types, style_keywords)
	suggested_providers = ['shadcn_ecosystem']

	return SearchPlan(
		primary_intent=primary_intent,
		parsed=parsed,
		component_types=component_types,
		alternative_terminology=alt_terms,
		style_keywords=style_keywords,
		theme=parsed.theme,
		page_context=page_context,
		suggested_providers=suggested_providers,
		suggested_registries=suggested_registries,
		planned_queries=planned_queries,
	)


def _primary_intent(
	parsed: ParsedQuery,
	component_types: list[str],
	page_context: list[str],
	styles: list[str],
) -> str:
	parts = []
	if component_types:
		parts.append(component_types[0])
	if page_context:
		parts.append(page_context[0])
	if styles:
		parts.extend(styles[:2])
	if parsed.theme:
		parts.append(parsed.theme)
	if not parts:
		return parsed.raw
	return ' '.join(parts)


def _build_planned_queries(
	parsed: ParsedQuery,
	component_types: list[str],
	page_context: list[str],
	styles: list[str],
	alt_terms: list[str],
) -> list[PlannedQuery]:
	queries: list[PlannedQuery] = []
	seen: set[str] = set()

	def add(text: str, confidence: float, pass_number: int, intent: str) -> None:
		norm = text.strip().lower()
		if not norm or norm in seen:
			return
		seen.add(norm)
		queries.append(
			PlannedQuery(text=text.strip(), confidence=confidence, pass_number=pass_number, intent=intent)
		)

	# Pass 1 — primary intent queries.
	add(parsed.raw, 1.0, 1, 'primary')
	for comp in component_types[:3]:
		add(comp, 0.95, 1, 'primary')
	for ctx in page_context[:2]:
		add(f'{ctx} {component_types[0]}' if component_types else ctx, 0.9, 1, 'primary')
	for style in styles[:3]:
		if component_types:
			add(f'{style} {component_types[0]}', 0.88, 1, 'primary')
		else:
			add(style, 0.85, 1, 'primary')
	if parsed.theme and component_types:
		add(f'{parsed.theme} {component_types[0]}', 0.87, 1, 'primary')

	# Pass 2 — expanded terminology.
	for term in alt_terms[:12]:
		add(term, 0.8, 2, 'expanded')
	for comp in component_types:
		for syn in COMPONENT_SYNONYMS.get(comp, ())[:4]:
			add(syn, 0.78, 2, 'expanded')
	if 'glass' in styles or 'glassmorphism' in styles:
		for comp in component_types or ['navbar']:
			add(f'glass {comp}', 0.82, 2, 'expanded')
	if parsed.animations:
		for comp in component_types or ['navigation']:
			add(f'animated {comp}', 0.8, 2, 'expanded')

	# Pass 3 — broader concepts.
	for comp in component_types:
		for broad in BROAD_CONCEPTS.get(comp, ())[:3]:
			add(broad, 0.6, 3, 'broad')
	if page_context:
		add(page_context[0], 0.55, 3, 'broad')

	queries.sort(key=lambda q: (-q.confidence, q.pass_number))
	return queries


def _expand_terminology(component_types: list[str]) -> list[str]:
	out: list[str] = []
	for comp in component_types:
		out.extend(COMPONENT_SYNONYMS.get(comp, ()))
	return _unique(out)


def _suggest_registries(
	parsed: ParsedQuery,
	component_types: list[str],
	styles: list[str],
) -> list[str]:
	registries: list[str] = []
	seen: set[str] = set()

	def add(ns: str) -> None:
		if ns not in seen:
			seen.add(ns)
			registries.append(ns)

	for comp in component_types:
		for ns in STYLE_REGISTRY_AFFINITY.get(comp, ()):
			add(ns)
	for style in styles:
		for ns in STYLE_REGISTRY_AFFINITY.get(style, ()):
			add(ns)
	for hint in parsed.search_hints:
		for ns in STYLE_REGISTRY_AFFINITY.get(hint, ()):
			add(ns)
	for ns in DEFAULT_REGISTRIES:
		add(ns)
	return registries[:20]


def _infer_component_types(parsed: ParsedQuery) -> list[str]:
	parts = [
		parsed.raw,
		*parsed.component_types,
		*parsed.keywords,
		*parsed.page_context,
	]
	text = ' '.join(parts).lower()
	inferred: list[str] = []
	for key in ('navbar', 'header', 'navigation', 'pricing', 'login', 'sidebar', 'hero', 'footer', 'button'):
		if key in text:
			inferred.append('navbar' if key in ('header', 'navigation') else key)
	return _unique(inferred)


def _unique(items: list[str]) -> list[str]:
	seen: set[str] = set()
	out: list[str] = []
	for item in items:
		key = item.strip().lower()
		if key and key not in seen:
			seen.add(key)
			out.append(item.strip())
	return out
