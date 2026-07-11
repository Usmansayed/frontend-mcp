"""Consensus engine — one senior-designer voice from many reviewer signals."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..models import ReviewFinding


_SEVERITY_RANK = {'blocking': 0, 'major': 1, 'minor': 2, 'advisory': 3}


@dataclass(slots=True)
class ConsensusResult:
	findings: list[ReviewFinding] = field(default_factory=list)
	merged_count: int = 0
	removed_duplicates: int = 0
	prioritized_recommendations: list[str] = field(default_factory=list)
	narrative: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'findings': [f.to_dict() for f in self.findings],
			'merged_count': self.merged_count,
			'removed_duplicates': self.removed_duplicates,
			'prioritized_recommendations': list(self.prioritized_recommendations),
			'narrative': self.narrative,
			'degraded': list(self.degraded),
		}


class ConsensusEngine:
	"""Dedupe, merge, prioritize — after all reviewers and providers contribute."""

	def synthesize(
		self,
		findings: list[ReviewFinding],
		*,
		user_task: str = '',
		reference_notes: list[str] | None = None,
	) -> ConsensusResult:
		degraded = ['consensus_engine_v1']
		groups = _group_findings(findings)
		merged: list[ReviewFinding] = []
		removed = 0

		for _key, group in groups.items():
			if len(group) > 1:
				removed += len(group) - 1
			merged.append(_merge_group(group))

		merged.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 9), f.category))
		recs = _prioritize_recommendations(merged)
		if reference_notes:
			recs = list(reference_notes[:3]) + recs
			recs = recs[:8]

		task = user_task or 'the interface'
		blocking = [f for f in merged if f.severity == 'blocking']
		major = [f for f in merged if f.severity == 'major']
		narrative = _compose_narrative(task, merged, blocking, major, recs)

		return ConsensusResult(
			findings=merged,
			merged_count=len(merged),
			removed_duplicates=removed,
			prioritized_recommendations=recs,
			narrative=narrative,
			degraded=degraded,
		)


def _normalize_key(f: ReviewFinding) -> str:
	msg = re.sub(r'\s+', ' ', f.message.lower().strip())[:80]
	return f'{f.category}:{msg}'


def _group_findings(findings: list[ReviewFinding]) -> dict[str, list[ReviewFinding]]:
	groups: dict[str, list[ReviewFinding]] = {}
	for f in findings:
		key = _normalize_key(f)
		# Also merge overflow duplicates across sources
		if 'overflow' in f.message.lower() or 'scrollwidth' in f.message.lower():
			key = 'layout:horizontal_overflow'
		if 'zero_size' in f.id or 'zero-size' in f.message.lower():
			key = 'accessibility:zero_size_clickable'
		groups.setdefault(key, []).append(f)
	return groups


def _merge_group(group: list[ReviewFinding]) -> ReviewFinding:
	group.sort(key=lambda f: _SEVERITY_RANK.get(f.severity, 9))
	primary = group[0]
	sources = sorted({f.source for f in group if f.source})
	evidence_parts = [f.evidence for f in group if getattr(f, 'evidence', '')]
	confidence = max(getattr(f, 'confidence', 0.7) for f in group)

	merged_rec = primary.recommendation
	for f in group[1:]:
		if f.recommendation and f.recommendation not in merged_rec:
			merged_rec = f'{merged_rec}; {f.recommendation}' if merged_rec else f.recommendation

	meta = dict(primary.metadata)
	meta['consensus_sources'] = sources
	if len(group) > 1:
		meta['merged_from'] = len(group)

	return ReviewFinding(
		id=primary.id,
		category=primary.category,
		severity=primary.severity,
		message=primary.message,
		rationale=primary.rationale or f'Confirmed by {len(sources)} reviewer(s): {", ".join(sources)}',
		recommendation=merged_rec[:500],
		source='consensus',
		pillar=primary.pillar,
		selector=primary.selector or next((f.selector for f in group if f.selector), None),
		region=primary.region,
		evidence=' | '.join(evidence_parts[:3]) if evidence_parts else primary.evidence,
		confidence=confidence,
	confirmed=primary.confirmed or len(sources) > 1,
		affected_element=primary.affected_element or primary.selector,
		metadata=meta,
	)


def _prioritize_recommendations(findings: list[ReviewFinding]) -> list[str]:
	recs: list[str] = []
	for f in findings:
		if f.severity in ('blocking', 'major') and f.recommendation:
			recs.append(f.recommendation)
		elif f.severity == 'minor' and f.recommendation and len(recs) < 6:
			recs.append(f.recommendation)
	return recs[:8]


def _compose_narrative(
	task: str,
	findings: list[ReviewFinding],
	blocking: list[ReviewFinding],
	major: list[ReviewFinding],
	recs: list[str],
) -> str:
	parts = [f'Design review for "{task}": {len(findings)} consolidated findings.']
	if blocking:
		parts.append(f'{len(blocking)} blocking issue(s) require immediate attention.')
	if major:
		parts.append(f'{len(major)} major issue(s) affect usability.')
	if not blocking and not major:
		parts.append('No blocking or major issues detected.')
	if recs:
		parts.append(f'Top priority: {recs[0]}')
	return ' '.join(parts)
