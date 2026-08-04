"""Candidate Intelligence — profile inference and normalization."""

__all__ = [
	'CandidateProfile',
	'infer_profile',
	'normalize_candidate',
	'normalize_candidates',
]


def __getattr__(name: str):  # noqa: ANN001
	if name == 'CandidateProfile':
		from navigation.figma_intelligence.models import CandidateProfile

		return CandidateProfile
	if name == 'infer_profile':
		from navigation.figma_intelligence.candidate_intelligence.inferrer import infer_profile

		return infer_profile
	if name == 'normalize_candidate':
		from navigation.figma_intelligence.candidate_intelligence.normalizer import normalize_candidate

		return normalize_candidate
	if name == 'normalize_candidates':
		from navigation.figma_intelligence.candidate_intelligence.normalizer import normalize_candidates

		return normalize_candidates
	raise AttributeError(name)
