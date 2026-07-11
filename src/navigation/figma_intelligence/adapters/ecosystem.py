"""Ecosystem adapters — Design Sense, Consistency, Component, Framework hints."""
from __future__ import annotations

from navigation.figma_intelligence.models import FigmaCandidate, FigmaExtractionResult, FigmaIntent


def gather_intelligence_hints(intent: FigmaIntent) -> tuple[dict[str, object], list[str]]:
	"""Collect search hints from sibling intelligence modules (scaffold)."""
	degraded: list[str] = []
	hints: dict[str, object] = {
		'framework': None,
		'component_stack': None,
		'token_families': [],
		'design_sense_profile': None,
		'pdg_summary': None,
	}

	if not intent.repo_root:
		degraded.append('hints_without_repo_root')
		return hints, degraded

	try:
		from pathlib import Path

		from navigation.framework_intelligence import FrameworkIntelligenceService

		meta = FrameworkIntelligenceService().detect(Path(intent.repo_root))
		if meta.framework:
			hints['framework'] = meta.framework
		if meta.primary_package:
			hints['component_stack'] = meta.primary_package
	except Exception:
		degraded.append('framework_hint_unavailable')

	return hints, degraded


def score_design_quality(
	candidate: FigmaCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = candidate.profile.confidence * 0.4
	if candidate.profile.patterns:
		score += 0.1
	return min(1.0, score), ['design_sense_eval_heuristic']


def score_consistency_fit(
	candidate: FigmaCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = 0.1 * len(candidate.profile.style)
	return min(1.0, score), ['consistency_eval_heuristic']


def score_component_reuse(
	candidate: FigmaCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = 0.08 * len(candidate.profile.components)
	return min(1.0, score), ['component_eval_heuristic']


def score_framework_fit(
	candidate: FigmaCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	return (0.5 if candidate.profile.framework else 0.0), ['framework_eval_heuristic']


def score_extraction_design_quality(
	extraction: FigmaExtractionResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not extraction.tokens and not extraction.components:
		return 0.0, ['deep_review_no_extraction_payload']
	score = 0.25
	score += min(0.35, 0.03 * len(extraction.tokens))
	score += min(0.25, 0.04 * len(extraction.components))
	score += min(0.15, 0.05 * len(extraction.patterns))
	return min(1.0, score), ['design_sense_extraction_heuristic']


def score_extraction_consistency(
	extraction: FigmaExtractionResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not extraction.tokens:
		return 0.0, ['consistency_no_tokens']
	return min(1.0, 0.2 + 0.02 * len(extraction.tokens)), ['consistency_extraction_heuristic']


def score_extraction_component_reuse(
	extraction: FigmaExtractionResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not extraction.components:
		return 0.0, ['component_no_components']
	return min(1.0, 0.15 + 0.05 * len(extraction.components)), ['component_extraction_heuristic']


def score_extraction_framework_fit(
	extraction: FigmaExtractionResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	meta = extraction.raw_payload.get('framework') if extraction.raw_payload else None
	if isinstance(meta, str) and meta.strip():
		return 0.7, []
	return (0.4 if extraction.components else 0.0), ['framework_extraction_heuristic']


def to_design_snapshot_payload(extraction: FigmaExtractionResult) -> dict[str, object]:
	"""Normalize extraction for Design Snapshot Engine (scaffold)."""
	return {
		'source': 'figma_intelligence',
		'provider_id': extraction.provider_id,
		'candidate_id': extraction.candidate_id,
		'tokens': extraction.tokens,
		'components': extraction.components,
		'variables': extraction.variables,
		'patterns': extraction.patterns,
	}
