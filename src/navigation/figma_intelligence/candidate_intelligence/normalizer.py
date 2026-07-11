"""Normalize raw discovery hits into intelligence-rich candidates."""
from __future__ import annotations

from navigation.figma_intelligence.candidate_intelligence.inferrer import infer_profile
from navigation.figma_intelligence.candidate_intelligence.profile import CandidateProfile
from navigation.figma_intelligence.models import FigmaCandidate


def normalize_candidate(candidate: FigmaCandidate) -> FigmaCandidate:
	"""Attach or refresh CandidateProfile without provider extraction."""
	if candidate.profile.confidence > 0 and candidate.profile.page_type:
		return candidate
	profile = infer_profile(
		title=candidate.title,
		tags=candidate.tags,
		metadata=candidate.metadata,
	)
	return _with_profile(candidate, profile)


def normalize_candidates(candidates: list[FigmaCandidate]) -> list[FigmaCandidate]:
	return [normalize_candidate(c) for c in candidates]


def _with_profile(candidate: FigmaCandidate, profile: CandidateProfile) -> FigmaCandidate:
	discovery_score = candidate.discovery_score or profile.confidence
	return FigmaCandidate(
		candidate_id=candidate.candidate_id,
		title=candidate.title,
		source=candidate.source,
		provider_id=candidate.provider_id,
		file_key=candidate.file_key,
		node_id=candidate.node_id,
		url=candidate.url,
		tags=candidate.tags,
		preview_ref=candidate.preview_ref,
		metadata=candidate.metadata,
		profile=profile,
		discovery_score=discovery_score,
	)
