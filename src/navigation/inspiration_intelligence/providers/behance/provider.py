"""Behance inspiration provider — HTTP search (fast, no bot flags observed)."""
from __future__ import annotations

import asyncio
import re
import urllib.parse
from typing import Any

from navigation.inspiration_intelligence.browser.fetch import http_get
from navigation.inspiration_intelligence.browser.policy import RateLimitTracker, detect_block_signal
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.behance.navigation import BEHANCE_NAVIGATION

_GALLERY = re.compile(r'href="(https?://[^"]*/gallery/(\d+)[^"]*)"', re.I)


class BehanceProvider:
	provider_id = 'behance'
	display_name = 'Behance'
	capabilities: frozenset[str] = frozenset({'discover', 'capture'})

	def __init__(self) -> None:
		self._tracker = RateLimitTracker()
		self._policy = self._tracker.policy_for('behance')

	async def discover_candidates(
		self,
		plan: InspirationSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: InspirationIntent,
		max_results: int = 20,
	) -> tuple[list[InspirationCandidate], list[str]]:
		_ = intent
		degraded: list[str] = []
		queries = [q.text for q in community_plan.executable_queries if q.execute]
		if not queries:
			queries = [plan.seed_query or community_plan.seed_query]
		query = queries[0].strip()
		if not query:
			return [], ['behance_empty_query']

		self._tracker.wait_if_needed(self.provider_id, self._policy)
		encoded = urllib.parse.quote(query)
		url = BEHANCE_NAVIGATION.search_url_pattern.format(query_slug=encoded)
		html, status, err = await asyncio.to_thread(http_get, url)
		if err:
			return [], [f'behance_fetch_failed:{err}']
		block = detect_block_signal(html, status_code=status)
		if block:
			return [], [f'behance_block:{block}']

		candidates: list[InspirationCandidate] = []
		seen: set[str] = set()
		for match in _GALLERY.finditer(html):
			gallery_url, gallery_id = match.group(1), match.group(2)
			if gallery_id in seen:
				continue
			seen.add(gallery_id)
			title = gallery_id
			window = html[max(0, match.start() - 300) : match.end() + 300]
			title_match = re.search(r'title="([^"]+)"', window, re.I)
			if title_match:
				title = title_match.group(1)
			candidates.append(
				InspirationCandidate(
					candidate_id=f'behance:{gallery_id}',
					title=title,
					source=self.provider_id,
					provider_id=self.provider_id,
					external_id=gallery_id,
					url=gallery_url.split('"')[0],
					metadata={'search_query': query, 'fetch_tier': 'http'},
					discovery_score=0.7,
				)
			)
			if len(candidates) >= max_results:
				break

		if not candidates:
			degraded.append('behance_parse_empty')
		return candidates, degraded

	async def capture_design(
		self,
		candidate: InspirationCandidate,
		*,
		intent: InspirationIntent,
	) -> InspirationCaptureResult:
		_ = intent
		from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail

		preview, _, degraded = await asyncio.to_thread(enrich_preview_from_detail, candidate.url)
		screenshot_refs = [preview] if preview else []
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			screenshot_refs=screenshot_refs,
			raw_payload={'detail_url': candidate.url},
			degraded=degraded if screenshot_refs else degraded + ['behance_capture_no_preview'],
		)

	async def health(self) -> dict[str, Any]:
		return {'provider_id': self.provider_id, 'status': 'ok', 'fetch_tiers': ['http']}
