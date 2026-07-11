"""Ecosystem adapters — Design Sense, Consistency, Component, Framework hints."""
from __future__ import annotations

from navigation.inspiration_intelligence.models import (
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
)


def gather_intelligence_hints(intent: InspirationIntent) -> tuple[dict[str, object], list[str]]:
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
	candidate: InspirationCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = candidate.profile.confidence * 0.4
	if candidate.profile.patterns:
		score += 0.1
	return min(1.0, score), ['design_sense_eval_heuristic']


def score_consistency_fit(
	candidate: InspirationCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = 0.1 * len(candidate.profile.style)
	return min(1.0, score), ['consistency_eval_heuristic']


def score_component_reuse(
	candidate: InspirationCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	score = 0.08 * len(candidate.profile.components)
	return min(1.0, score), ['component_eval_heuristic']


def score_framework_fit(
	candidate: InspirationCandidate,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	return (0.5 if candidate.profile.framework else 0.0), ['framework_eval_heuristic']


def score_capture_design_quality(
	capture: InspirationCaptureResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not capture.screenshot_refs:
		return 0.0, ['deep_review_no_screenshots']
	score = 0.35
	score += min(0.35, 0.15 * len(capture.screenshot_refs))
	score += min(0.2, 0.05 * len(capture.patterns))
	score += min(0.1, 0.04 * len(capture.components))
	return min(1.0, score), ['design_sense_capture_heuristic']


def score_capture_consistency(
	capture: InspirationCaptureResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not capture.screenshot_refs:
		return 0.0, ['consistency_no_screenshots']
	return min(1.0, 0.25 + 0.1 * len(capture.screenshot_refs)), ['consistency_capture_heuristic']


def score_capture_component_reuse(
	capture: InspirationCaptureResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	if not capture.components:
		return 0.0, ['component_no_components']
	return min(1.0, 0.15 + 0.05 * len(capture.components)), ['component_capture_heuristic']


def score_capture_framework_fit(
	capture: InspirationCaptureResult,
	*,
	repo_root: str,
) -> tuple[float, list[str]]:
	_ = repo_root
	meta = capture.raw_payload.get('framework') if capture.raw_payload else None
	if isinstance(meta, str) and meta.strip():
		return 0.7, []
	return (0.4 if capture.components else 0.0), ['framework_capture_heuristic']


def to_design_snapshot_payload(capture: InspirationCaptureResult) -> dict[str, object]:
	"""Normalize capture for Design Snapshot Engine (scaffold)."""
	return {
		'source': 'inspiration_intelligence',
		'provider_id': capture.provider_id,
		'candidate_id': capture.candidate_id,
		'screenshot_refs': capture.screenshot_refs,
		'patterns': capture.patterns,
		'components': capture.components,
	}
