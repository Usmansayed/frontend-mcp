"""Normalize raw discovery hits into intelligence-rich candidates."""
from __future__ import annotations

from navigation.inspiration_intelligence.candidate_intelligence.inferrer import infer_profile
from navigation.inspiration_intelligence.candidate_intelligence.profile import CandidateProfile
from navigation.inspiration_intelligence.models import InspirationCandidate


def normalize_candidate(candidate: InspirationCandidate) -> InspirationCandidate:
	"""Attach or refresh CandidateProfile without provider capture."""
	if candidate.profile.confidence > 0 and candidate.profile.page_type:
		return candidate
	profile = infer_profile(
		title=candidate.title,
		tags=candidate.tags,
		metadata=candidate.metadata,
	)
	return _with_profile(candidate, profile)


def normalize_candidates(candidates: list[InspirationCandidate]) -> list[InspirationCandidate]:
	return [normalize_candidate(c) for c in candidates]


def _with_profile(candidate: InspirationCandidate, profile: CandidateProfile) -> InspirationCandidate:
	discovery_score = candidate.discovery_score or profile.confidence
	return InspirationCandidate(
		candidate_id=candidate.candidate_id,
		title=candidate.title,
		source=candidate.source,
		provider_id=candidate.provider_id,
		external_id=candidate.external_id,
		url=candidate.url,
		tags=candidate.tags,
		preview_ref=candidate.preview_ref,
		metadata=candidate.metadata,
		profile=profile,
		discovery_score=discovery_score,
	)
