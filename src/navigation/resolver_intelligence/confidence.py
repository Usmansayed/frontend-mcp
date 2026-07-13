"""Deterministic confidence scoring for resolver matches."""
from __future__ import annotations

from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    ResolverMatch,
    ResolverStatus,
)


def score_route_match(
    *,
    exact_path: bool,
    file_on_disk: bool,
    dynamic_segment: bool,
    match_count: int,
) -> tuple[float, ConfidenceLevel, ResolverStatus]:
    score = 0.0
    if exact_path:
        score += 0.5
    if file_on_disk:
        score += 0.3
    score += 0.1  # framework plugin exact match
    if dynamic_segment:
        score -= 0.2

    if match_count > 1:
        return score, ConfidenceLevel.MEDIUM, ResolverStatus.AMBIGUOUS
    if match_count == 0:
        return 0.0, ConfidenceLevel.NONE, ResolverStatus.NOT_FOUND

    if score >= 0.75:
        return min(score, 1.0), ConfidenceLevel.HIGH, ResolverStatus.RESOLVED
    if score >= 0.45:
        return score, ConfidenceLevel.MEDIUM, ResolverStatus.LOW_CONFIDENCE
    return score, ConfidenceLevel.LOW, ResolverStatus.LOW_CONFIDENCE


def fallback_for_status(status: ResolverStatus) -> str:
    if status == ResolverStatus.AMBIGUOUS:
        return "validate_claim"
    if status == ResolverStatus.LOW_CONFIDENCE:
        return "validate_claim"
    if status in (ResolverStatus.NOT_FOUND, ResolverStatus.UNSUPPORTED):
        return "host_search"
    return "correlate_live_only"
