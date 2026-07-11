"""Community Intelligence — expand one query into ranked semantic searches."""
from __future__ import annotations

import re

from navigation.inspiration_intelligence.browser.policy import is_fast_mode
from navigation.inspiration_intelligence.community_intelligence.lexicon import (
	COMPONENT_SYNONYMS,
	DESIGN_LANGUAGES,
	EXECUTION_CONFIDENCE_THRESHOLD,
	INDUSTRIES,
	PAGE_COMPONENT_EXPANSION,
	PAGE_SYNONYMS,
	STYLE_ALIASES,
	STYLE_MODIFIERS,
)
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationIntent,
	InspirationSearchPlan,
	PlannedCommunityQuery,
)


def build_community_plan(intent: InspirationIntent, search_plan: InspirationSearchPlan) -> CommunitySearchPlan:
	"""Expand seed intent into many ranked community searches."""
	text = (intent.raw_query or '').strip().lower()
	degraded: list[str] = list(search_plan.degraded)

	page_types = _detect_page_types(text, intent)
	industries = _detect_industries(text, intent)
	styles = _detect_styles(text, intent)
	design_languages = _detect_design_languages(text)
	components = _detect_components(text, page_types)

	queries: list[PlannedCommunityQuery] = []
	seen: set[str] = set()

	def add(
		query_text: str,
		*,
		confidence: float,
		pass_number: int,
		intent_label: str,
		expansion_kind: str,
	) -> None:
		norm = re.sub(r'\s+', ' ', query_text.strip().lower())
		if not norm or norm in seen:
			return
		seen.add(norm)
		execute = confidence >= EXECUTION_CONFIDENCE_THRESHOLD
		queries.append(
			PlannedCommunityQuery(
				text=query_text.strip(),
				confidence=confidence,
				pass_number=pass_number,
				intent_label=intent_label,
				expansion_kind=expansion_kind,
				execute=execute,
			)
		)

	# Pass 1 — primary intent.
	add(intent.raw_query, confidence=1.0, pass_number=1, intent_label='primary', expansion_kind='seed')
	for page in page_types[:2]:
		add(f'{page} ui kit', confidence=0.95, pass_number=1, intent_label='primary', expansion_kind='page_type')
	for industry in industries[:2]:
		add(f'{industry} {page_types[0] if page_types else "dashboard"}', confidence=0.92, pass_number=1, intent_label='primary', expansion_kind='industry')

	# Pass 2 — synonyms + style.
	for page in page_types:
		for synonym in PAGE_SYNONYMS.get(page, [])[:3]:
			add(synonym, confidence=0.88, pass_number=2, intent_label='synonym', expansion_kind='page_synonym')
			for style in styles[:2]:
				add(f'{style} {synonym}', confidence=0.85, pass_number=2, intent_label='synonym', expansion_kind='style_page')
	for lang, aliases in design_languages.items():
		add(f'{lang} {page_types[0] if page_types else "ui"}', confidence=0.86, pass_number=2, intent_label='style', expansion_kind='design_language')
		for alias in aliases[:2]:
			add(alias, confidence=0.82, pass_number=2, intent_label='style', expansion_kind='design_language')

	# Pass 3 — component expansion + broad industry.
	for page in page_types:
		for component in PAGE_COMPONENT_EXPANSION.get(page, [])[:4]:
			add(f'{component} {page}', confidence=0.78, pass_number=3, intent_label='component', expansion_kind='page_component')
			for alt in COMPONENT_SYNONYMS.get(component, [])[:1]:
				add(f'{alt} {page}', confidence=0.72, pass_number=3, intent_label='component', expansion_kind='component_synonym')
	for industry, aliases in INDUSTRIES.items():
		if industry in industries:
			for alias in aliases[:2]:
				add(alias, confidence=0.7, pass_number=3, intent_label='broad', expansion_kind='industry_broad')

	# Framework / stack hint from search plan.
	stack = search_plan.filters.get('component_stack')
	if isinstance(stack, str) and stack.strip():
		add(f'{stack} {page_types[0] if page_types else intent.raw_query}', confidence=0.84, pass_number=2, intent_label='stack', expansion_kind='framework_hint')

	queries.sort(key=lambda q: (-q.confidence, q.pass_number))
	executable = [q for q in queries if q.execute]

	if is_fast_mode() and executable:
		primary = next((q for q in executable if q.expansion_kind == 'seed'), executable[0])
		executable = [primary]
		degraded.append('community_fast_mode_single_query')

	if not executable:
		degraded.append('community_no_executable_queries')
		executable = queries[:5]
		for q in executable:
			q.execute = True

	return CommunitySearchPlan(
		seed_query=intent.raw_query,
		page_types=page_types,
		industries=industries,
		styles=styles,
		design_languages=list(design_languages.keys()),
		components=components,
		planned_queries=queries,
		executable_queries=executable,
		degraded=degraded,
	)


def _detect_page_types(text: str, intent: InspirationIntent) -> list[str]:
	found: list[str] = []
	for page in PAGE_SYNONYMS:
		if page in text or page in intent.target_styles:
			found.append(page)
	for style_target in intent.target_styles:
		if style_target in PAGE_SYNONYMS and style_target not in found:
			found.append(style_target)
	if not found and any(w in text for w in ('admin', 'analytics', 'control center')):
		found.append('dashboard')
	return list(dict.fromkeys(found))


def _detect_industries(text: str, intent: InspirationIntent) -> list[str]:
	found: list[str] = []
	for industry in INDUSTRIES:
		if industry in text or industry in intent.target_styles:
			found.append(industry)
	for token in ('b2b', 'b2c', 'startup', 'enterprise'):
		if token in text:
			found.append('saas')
			break
	return list(dict.fromkeys(found))


def _detect_styles(text: str, intent: InspirationIntent) -> list[str]:
	found = [s for s in STYLE_MODIFIERS if s in text]
	for raw, canonical in STYLE_ALIASES.items():
		if raw in text and canonical not in found:
			found.append(canonical)
	return list(dict.fromkeys(found))


def _detect_design_languages(text: str) -> dict[str, list[str]]:
	out: dict[str, list[str]] = {}
	for lang, aliases in DESIGN_LANGUAGES.items():
		if lang in text or any(alias in text for alias in aliases):
			out[lang] = aliases
	return out


def _detect_components(text: str, page_types: list[str]) -> list[str]:
	found: list[str] = []
	for component in COMPONENT_SYNONYMS:
		if component in text:
			found.append(component)
	for page in page_types:
		found.extend(PAGE_COMPONENT_EXPANSION.get(page, [])[:3])
	return list(dict.fromkeys(found))
