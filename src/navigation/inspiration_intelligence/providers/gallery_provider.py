"""Gallery site provider — resilient HTTP + perception browser discovery."""
from __future__ import annotations

from typing import Any

from navigation.inspiration_intelligence.browser.resilient_fetch import ResilientFetchConfig, ResilientPageFetcher
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge


class GallerySiteProvider:
	"""Production gallery provider — HTTP first, headed perception browser fallback."""

	def __init__(self, navigation: ProviderNavigationKnowledge, fetch_config: ResilientFetchConfig) -> None:
		self._navigation = navigation
		self._fetch_config = fetch_config
		self.provider_id = navigation.provider_id
		self.display_name = navigation.display_name
		self.capabilities: frozenset[str] = frozenset({'discover', 'capture'})

	async def discover_candidates(
		self,
		plan: InspirationSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: InspirationIntent,
		max_results: int = 20,
	) -> tuple[list[InspirationCandidate], list[str]]:
		_ = intent, plan
		degraded: list[str] = []
		queries = [q.text for q in community_plan.executable_queries if q.execute]
		if not queries:
			queries = [community_plan.seed_query]
		query = next((q.strip() for q in queries if q.strip()), '')
		if not query:
			return [], [f'{self.provider_id}_empty_query']

		fetcher = ResilientPageFetcher(self._fetch_config)
		result = await fetcher.fetch_hits(query, max_hits=max_results)
		degraded.extend(result.degraded)

		hits = _filter_hits(self.provider_id, result.hits)
		if not result.ok or not hits:
			degraded.append(f'{self.provider_id}_discovery_empty')
			return [], degraded

		candidates: list[InspirationCandidate] = []
		for hit in hits:
			external_id = hit.get('external_id', '')
			if not external_id:
				continue
			candidates.append(
				InspirationCandidate(
					candidate_id=f'{self.provider_id}:{external_id}',
					title=hit.get('title', external_id),
					source=self.provider_id,
					provider_id=self.provider_id,
					external_id=external_id,
					url=hit.get('url', self._navigation.detail_url(external_id)),
					preview_ref=hit.get('preview_url', ''),
					metadata={
						'search_query': query,
						'fetch_tier': result.fetch_tier,
						'source_url': result.url,
					},
					discovery_score=_query_match_score(query, hit.get('title', '')),
				)
			)

		candidates.sort(key=lambda c: c.discovery_score, reverse=True)
		return candidates[:max_results], degraded

	async def capture_design(
		self,
		candidate: InspirationCandidate,
		*,
		intent: InspirationIntent,
	) -> InspirationCaptureResult:
		_ = intent
		import asyncio

		from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail

		degraded: list[str] = []
		screenshot_refs: list[str] = []

		if candidate.preview_ref:
			screenshot_refs.append(candidate.preview_ref)
			degraded.append('capture_tier:discovery_preview')

		if not screenshot_refs and candidate.url:
			preview, _, og_deg = await asyncio.to_thread(enrich_preview_from_detail, candidate.url)
			degraded.extend(og_deg)
			if preview:
				screenshot_refs.append(preview)
				degraded.append('capture_tier:og_image')

		if not screenshot_refs and candidate.url:
			from navigation.inspiration_intelligence.browser.policy import RateLimitTracker
			from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

			try:
				tracker = RateLimitTracker()
				policy = tracker.policy_for(self.provider_id)
				async with InspirationBrowserSession(
					provider_id=self.provider_id,
					policy=policy,
				) as session:
					path, ss_deg = await session.screenshot_url(candidate.url)
					degraded.extend(ss_deg)
					if path:
						screenshot_refs.append(path)
						degraded.append('capture_tier:perception_screenshot')
			except Exception as exc:
				degraded.append(f'capture_screenshot_failed:{exc}')

		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			screenshot_refs=screenshot_refs,
			raw_payload={'detail_url': candidate.url, 'external_id': candidate.external_id},
			degraded=degraded if screenshot_refs else degraded + [f'{self.provider_id}_capture_no_preview'],
		)

	async def health(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'status': 'ok',
			'fetch_tiers': ['http', 'perception_browser', 'perception_browser_retry', 'og_image'],
			'browser_required': self._fetch_config.browser_required,
		}


def _filter_hits(provider_id: str, hits: list[dict[str, str]]) -> list[dict[str, str]]:
	if provider_id != 'onepagelove':
		return hits
	from navigation.inspiration_intelligence.providers.gallery_parse import OPL_RESERVED_SLUGS

	filtered: list[dict[str, str]] = []
	for hit in hits:
		slug = hit.get('external_id', '')
		if slug and slug not in OPL_RESERVED_SLUGS:
			filtered.append(hit)
	return filtered


def _query_match_score(query: str, title: str) -> float:
	q_tokens = {t for t in query.lower().split() if len(t) > 2}
	if not q_tokens:
		return 0.5
	title_l = title.lower()
	hits = sum(1 for t in q_tokens if t in title_l)
	return min(0.92, 0.4 + 0.14 * hits)
