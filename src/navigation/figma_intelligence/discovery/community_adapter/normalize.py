"""Convert CommunityDiscoveryHit → FigmaCandidate for downstream intelligence."""
from __future__ import annotations

from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.models import FigmaCandidate


def hit_to_candidate(hit: CommunityDiscoveryHit) -> FigmaCandidate:
	metadata = dict(hit.extra)
	if hit.description:
		metadata['description'] = hit.description
	if hit.author:
		metadata['author'] = hit.author
	if hit.design_system:
		metadata['design_system'] = hit.design_system
	if hit.likes is not None:
		metadata['likes'] = hit.likes
	if hit.downloads is not None:
		metadata['downloads'] = hit.downloads
	if hit.source_backend:
		metadata['discovery_backend'] = hit.source_backend
	if hit.extra.get('content_id'):
		metadata['content_id'] = hit.extra['content_id']
	if hit.extra.get('resource_id'):
		metadata['resource_id'] = hit.extra['resource_id']

	return FigmaCandidate(
		candidate_id=hit.hit_id,
		title=hit.title,
		source='community',
		provider_id='',  # assigned at extraction time by Selection Planner
		file_key=hit.file_key,
		url=hit.community_url,
		tags=list(hit.tags),
		preview_ref=hit.preview_image,
		metadata=metadata,
		discovery_score=hit.discovery_score,
	)


def hits_to_candidates(hits: list[CommunityDiscoveryHit]) -> list[FigmaCandidate]:
	return [hit_to_candidate(h) for h in hits]
