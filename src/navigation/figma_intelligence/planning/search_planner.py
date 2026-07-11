"""Search planning — multi-intelligence hints before provider calls."""
from __future__ import annotations

from navigation.figma_intelligence.adapters.ecosystem import gather_intelligence_hints
from navigation.figma_intelligence.models import FigmaIntent, FigmaIntentKind, FigmaSearchPlan


def build_search_plan(
	intent: FigmaIntent,
	*,
	provider_preference: str | None = None,
) -> FigmaSearchPlan:
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

	return FigmaSearchPlan(
		seed_query=queries,
		provider_ids=provider_ids,
		filters=filters,
		intelligence_hints=hints,
		degraded=degraded,
	)


def _build_seed_query(intent: FigmaIntent) -> str:
	return intent.raw_query.strip() or intent.kind.value


def _resolve_providers(intent: FigmaIntent, preference: str | None) -> list[str]:
	if preference:
		return [preference]
	# Official MCP better for owned files; Console for community + DS kit
	if intent.kind in {FigmaIntentKind.EXTRACT_DS, FigmaIntentKind.COMPARE}:
		return ['official_figma', 'figma_console']
	return ['figma_console', 'official_figma']
