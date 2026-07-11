"""Search planning — multi-intelligence hints before provider calls."""
from __future__ import annotations

from navigation.inspiration_intelligence.adapters.ecosystem import gather_intelligence_hints
from navigation.inspiration_intelligence.models import (
	InspirationIntent,
	InspirationIntentKind,
	InspirationSearchPlan,
)

DEFAULT_PROVIDER_PRIORITY: list[str] = [
	'dribbble',
	'behance',
	'onepagelove',
	'awwwards',
	'siteinspire',
	'godly',
	'land-book',
]


def build_search_plan(
	intent: InspirationIntent,
	*,
	provider_preference: str | None = None,
) -> InspirationSearchPlan:
	degraded: list[str] = []
	hints, hint_degraded = gather_intelligence_hints(intent)
	degraded.extend(hint_degraded)

	queries = _build_seed_query(intent)
	provider_ids = _resolve_providers(intent, provider_preference)

	filters: dict[str, object] = {
		'framework': hints.get('framework'),
		'token_families': hints.get('token_families', []),
		'component_stack': hints.get('component_stack'),
		'style_targets': intent.target_styles,
	}

	return InspirationSearchPlan(
		seed_query=queries,
		provider_ids=provider_ids,
		filters=filters,
		intelligence_hints=hints,
		degraded=degraded,
	)


def _build_seed_query(intent: InspirationIntent) -> str:
	return intent.raw_query.strip() or intent.kind.value


def _resolve_providers(intent: InspirationIntent, preference: str | None) -> list[str]:
	if preference:
		return [preference, *[p for p in DEFAULT_PROVIDER_PRIORITY if p != preference]]
	if intent.kind in {InspirationIntentKind.COMPARE, InspirationIntentKind.REUSE_PATTERN}:
		return list(DEFAULT_PROVIDER_PRIORITY)
	return list(DEFAULT_PROVIDER_PRIORITY)
