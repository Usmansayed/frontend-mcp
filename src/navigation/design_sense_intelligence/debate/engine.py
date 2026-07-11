"""Reviewer debate — remove findings refuted by peers or snapshot facts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot

from ..models import ReviewFinding, ReviewRequest
from ..snapshot_access import resolve_snapshot

_RATIO_RE = re.compile(r'ratio[=:]?\s*([0-9.]+)', re.IGNORECASE)


@dataclass(slots=True)
class DebateResult:
	findings: list[ReviewFinding] = field(default_factory=list)
	removed_count: int = 0
	challenges: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'findings': [f.to_dict() for f in self.findings],
			'removed_count': self.removed_count,
			'challenges': list(self.challenges),
			'degraded': list(self.degraded),
		}


class ReviewerDebateEngine:
	"""Let reviewers challenge each other before consensus merge."""

	def run(
		self,
		findings: list[ReviewFinding],
		*,
		request: ReviewRequest | None = None,
		snapshot: DesignSnapshot | None = None,
	) -> DebateResult:
		if snapshot is None and request is not None:
			snapshot = resolve_snapshot(request)

		kept: list[ReviewFinding] = []
		challenges: list[str] = []
		removed = 0

		for f in findings:
			reason = _refutation_reason(f, findings, snapshot)
			if reason:
				removed += 1
				challenges.append(f'{f.id}: {reason}')
				continue
			kept.append(f)

		return DebateResult(
			findings=kept,
			removed_count=removed,
			challenges=challenges,
			degraded=['reviewer_debate_v1'] if removed else [],
		)


def _refutation_reason(
	finding: ReviewFinding,
	all_findings: list[ReviewFinding],
	snapshot: DesignSnapshot | None,
) -> str | None:
	if finding.severity in ('minor', 'advisory') and not finding.evidence:
		if 'contrast' in finding.message.lower() and not _has_contrast_evidence(finding):
			return 'debate:contrast claim without measured ratio'

	snapshot_reason = _refuted_by_snapshot(finding, snapshot)
	if snapshot_reason:
		return snapshot_reason

	peer_reason = _refuted_by_peer(finding, all_findings, snapshot)
	if peer_reason:
		return peer_reason

	return None


def _refuted_by_snapshot(finding: ReviewFinding, snapshot: DesignSnapshot | None) -> str | None:
	if snapshot is None:
		return None

	msg = finding.message.lower()

	if 'contrast' in msg and finding.category in ('color', 'accessibility'):
		if not snapshot.colors.wcag_failures:
			if not _has_contrast_evidence(finding):
				return 'accessibility:snapshot shows no WCAG contrast failures'
		else:
			ratio = _parse_ratio(finding.evidence or finding.message)
			if ratio is not None and ratio >= 4.5:
				return 'accessibility:contrast ratio meets WCAG AA'

	if 'unlabeled' in msg and not snapshot.accessibility.unlabeled_interactive:
		return 'accessibility:no unlabeled interactive elements in snapshot'

	if ('overflow' in msg or 'scrollwidth' in msg) and finding.severity != 'blocking':
		layout_issues = snapshot.layout.issues or []
		has_overflow = any(
			'overflow' in str(i.get('kind', '')).lower() for i in layout_issues
		)
		if not has_overflow and 'scrollwidth' not in finding.evidence.lower():
			return 'layout:snapshot shows no overflow issues'

	if finding.id == 'color_raw_values' and snapshot.colors.raw_color_count == 0:
		return 'color:no raw color values in snapshot'

	return None


def _refuted_by_peer(
	finding: ReviewFinding,
	all_findings: list[ReviewFinding],
	snapshot: DesignSnapshot | None,
) -> str | None:
	if finding.category == 'color' and 'contrast' in finding.message.lower():
		# Accessibility lane did not corroborate and snapshot has no failures
		a11y_contrast = [
			f for f in all_findings
			if f.source == 'accessibility_reviewer' and 'contrast' in f.message.lower()
		]
		if snapshot is not None and not snapshot.colors.wcag_failures and not a11y_contrast:
			if not _has_contrast_evidence(finding):
				return 'accessibility_reviewer:WCAG passes (no corroboration)'

	if finding.id == 'ms_tokens_unknown':
		return 'layout:design tokens available from snapshot'

	if finding.category == 'tokens' and 'not supplied' in finding.message.lower():
		return 'tokens:design tokens present'

	return None


def _has_contrast_evidence(finding: ReviewFinding) -> bool:
	if finding.evidence and 'ratio=' in finding.evidence.lower():
		ratio = _parse_ratio(finding.evidence)
		return ratio is not None and ratio < 4.5
	return False


def _parse_ratio(text: str) -> float | None:
	match = _RATIO_RE.search(text)
	if not match:
		match = re.search(r'([0-9.]+)\s*:\s*1', text)
	if not match:
		return None
	try:
		return float(match.group(1))
	except ValueError:
		return None
