"""Parallel provider search execution."""
from __future__ import annotations

import asyncio
from typing import Any

from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory
from navigation.resource_intelligence.providers.protocol import ResourceProvider


async def execute_provider_searches(
	providers: list[tuple[str, ResourceProvider]],
	*,
	query: str,
	category: ResourceCategory,
	max_results: int,
) -> tuple[list[ResourceAssetRef], list[str], list[str]]:
	all_assets: list[ResourceAssetRef] = []
	all_degraded: list[str] = []
	queried: list[str] = []

	async def _one(provider_id: str, provider: ResourceProvider) -> tuple[str, list[ResourceAssetRef], list[str]]:
		try:
			assets, deg = await provider.search(query, category=category, max_results=max_results)
			return provider_id, assets, deg
		except Exception as exc:
			return provider_id, [], [f'{provider_id}_search_failed:{exc}']

	results = await asyncio.gather(*[_one(pid, p) for pid, p in providers])
	for provider_id, assets, deg in results:
		queried.append(provider_id)
		all_assets.extend(assets)
		all_degraded.extend(deg)
	return all_assets, all_degraded, queried
