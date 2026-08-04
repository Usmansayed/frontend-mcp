"""Search planning — multi-intelligence hints before provider calls."""
from __future__ import annotations

from navigation.inspiration_intelligence.adapters.ecosystem import gather_intelligence_hints
from navigation.inspiration_intelligence.models import (
	InspirationIntent,
	InspirationIntentKind,
	InspirationSearchPlan,
)

# HTTP/CDN-friendly providers first — minimize Chromium for discovery.
# Fast mode (default) uses only the first two; deep research gets the full list.
# land-book is registered but omitted from default cascades (unreliable / slow).
DEFAULT_PROVIDER_PRIORITY: list[str] = [
	'onepagelove',
	'lapa',
	'behance',
	'httpster',
	'dribbble',
	'awwwards',
	'siteinspire',
	'godly',
]

FAST_HTTP_PROVIDER_PRIORITY: list[str] = [
	'onepagelove',
	'lapa',
	'behance',
	'httpster',
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
	from navigation.inspiration_intelligence.browser.policy import is_fast_mode

	base = (
		list(FAST_HTTP_PROVIDER_PRIORITY)
		if is_fast_mode()
		else list(DEFAULT_PROVIDER_PRIORITY)
	)
	# Explicit preference always leads; browser galleries stay available when asked.
	if preference:
		if preference not in base:
			# User asked for a deep gallery — expand beyond fast HTTP set.
			base = list(DEFAULT_PROVIDER_PRIORITY)
		return [preference, *[p for p in base if p != preference]]
	if intent.kind in {InspirationIntentKind.COMPARE, InspirationIntentKind.REUSE_PATTERN}:
		# Compare / reuse benefits from broader coverage.
		return list(DEFAULT_PROVIDER_PRIORITY)
	return base
