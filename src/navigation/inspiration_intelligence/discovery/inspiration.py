"""Inspiration discovery — priority provider search with production guarantees."""
from __future__ import annotations

from navigation.inspiration_intelligence.browser.policy import RateLimitTracker
from navigation.inspiration_intelligence.candidate_intelligence.normalizer import normalize_candidates
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.manager import (
	HIGH_CONFIDENCE_SCORE,
	InspirationProviderRegistry,
	PRODUCTION_MIN_CANDIDATES,
	RESCUE_PROVIDER_ORDER,
	min_high_confidence_hits,
)


def has_enough_high_confidence(
	candidates: list[InspirationCandidate],
	*,
	max_results: int,
	threshold: float = HIGH_CONFIDENCE_SCORE,
	min_hits: int | None = None,
) -> bool:
	"""True when discovery can stop cascading to lower-priority providers."""
	if len(candidates) < PRODUCTION_MIN_CANDIDATES:
		return False
	if min_hits is None:
		min_hits = min_high_confidence_hits()
	needed = min(min_hits, max_results)
	high = [
		c
		for c in candidates
		if max(c.discovery_score, c.profile.confidence) >= threshold
	]
	return len(high) >= needed


async def _rescue_discovery(
	registry: InspirationProviderRegistry,
	search_plan: InspirationSearchPlan,
	community_plan: CommunitySearchPlan,
	*,
	intent: InspirationIntent,
	max_results: int,
) -> tuple[list[InspirationCandidate], list[str]]:
	"""Last-resort pass — hit the most reliable providers before giving up."""
	degraded = ['discovery_rescue_pass']
	seen: set[str] = set()
	candidates: list[InspirationCandidate] = []

	for provider_id in RESCUE_PROVIDER_ORDER:
		provider = registry.get(provider_id)
		if provider is None:
			continue
		batch, batch_degraded = await provider.discover_candidates(
			search_plan,
			community_plan=community_plan,
			intent=intent,
			max_results=max_results,
		)
		degraded.extend(batch_degraded)
		degraded.append(f'rescue_tried:{provider_id}')
		for candidate in batch:
			key = candidate.candidate_id or f'{candidate.provider_id}:{candidate.external_id}'
			if key in seen:
				continue
			seen.add(key)
			candidates.append(candidate)
		if candidates:
			degraded.append(f'discovery_rescue_ok:{provider_id}')
			return normalize_candidates(candidates)[:max_results], degraded

	degraded.append('discovery_rescue_failed')
	return [], degraded


async def discover_inspiration(
	search_plan: InspirationSearchPlan,
	community_plan: CommunitySearchPlan,
	*,
	intent: InspirationIntent,
	max_results: int,
	providers: InspirationProviderRegistry | None = None,
	skip_usage_gate: bool = False,
) -> tuple[list[InspirationCandidate], list[str]]:
	"""Query inspiration providers in priority order; guarantee results when possible."""
	from navigation.inspiration_intelligence.browser.usage_gate import InspirationUsageGate

	degraded: list[str] = []
	if not skip_usage_gate:
		gate = InspirationUsageGate()
		check = gate.check(purpose=intent.kind.value)
		if not check.allowed:
			degraded.append(f'inspiration_usage_gate:{check.reason}')
			degraded.append(f'inspiration_retry_in_s:{int(check.seconds_until_ready)}')
			return [], degraded
		gate.record_run(purpose=intent.kind.value, provider_ids=search_plan.provider_ids)

	registry = providers or InspirationProviderRegistry()
	seen: set[str] = set()
	candidates: list[InspirationCandidate] = []
	providers_searched: list[str] = []
	rate_tracker = RateLimitTracker()

	for provider_id in search_plan.provider_ids:
		provider = registry.get(provider_id)
		if provider is None:
			degraded.append(f'discovery_missing_provider:{provider_id}')
			continue

		policy = rate_tracker.policy_for(provider_id)
		if rate_tracker.over_budget(provider_id, policy):
			degraded.append(f'discovery_rate_budget:{provider_id}')
			continue

		remaining = max_results - len(candidates)
		if remaining <= 0 and len(candidates) >= PRODUCTION_MIN_CANDIDATES:
			break

		batch, batch_degraded = await provider.discover_candidates(
			search_plan,
			community_plan=community_plan,
			intent=intent,
			max_results=remaining if remaining > 0 else max_results,
		)
		providers_searched.append(provider_id)
		degraded.extend(batch_degraded)

		for candidate in batch:
			key = candidate.candidate_id or f'{candidate.provider_id}:{candidate.external_id}'
			if key in seen:
				continue
			seen.add(key)
			candidates.append(candidate)

		candidates = normalize_candidates(candidates)
		if has_enough_high_confidence(candidates, max_results=max_results):
			degraded.append(f'discovery_early_stop:{provider_id}')
			break

	if providers_searched:
		degraded.append(f'discovery_providers_searched:{",".join(providers_searched)}')

	if not candidates:
		rescue, rescue_deg = await _rescue_discovery(
			registry,
			search_plan,
			community_plan,
			intent=intent,
			max_results=max_results,
		)
		degraded.extend(rescue_deg)
		candidates = rescue

	if not candidates:
		degraded.append('inspiration_discovery_empty')

	return candidates[:max_results], degraded
