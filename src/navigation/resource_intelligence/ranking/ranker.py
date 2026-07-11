"""Rank resource assets by license fit and query relevance."""
from __future__ import annotations

from navigation.resource_intelligence.models import ResourceAssetRef, ResourceDiscoveryRequest


def rank_assets(assets: list[ResourceAssetRef], request: ResourceDiscoveryRequest) -> list[ResourceAssetRef]:
	query_tokens = {t for t in request.query.lower().split() if len(t) > 1}

	def sort_key(asset: ResourceAssetRef) -> tuple[float, float]:
		title = asset.title.lower()
		tag_text = ' '.join(asset.tags).lower()
		text = f'{title} {tag_text} {asset.resource_id.lower()}'
		overlap = sum(1 for t in query_tokens if t in text)
		svg_bonus = 0.15 if request.prefer_svg and asset.format == 'svg' else 0.0
		host_bonus = 0.1 if request.prefer_self_hosted and (asset.license and asset.license.self_hostable) else 0.0
		relevance = overlap + svg_bonus + host_bonus
		return (asset.score + relevance, relevance)

	return sorted(assets, key=sort_key, reverse=True)
