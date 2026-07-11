"""Shared reviewer helpers."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest


def findings_from_visual_insights(
	request: ReviewRequest,
	*,
	category: str,
	source: str,
	kind_filter: str | None = None,
) -> list[ReviewFinding]:
	insights = request.visual_insights or {}
	out: list[ReviewFinding] = []
	for issue in insights.get('issues') or []:
		kind = str(issue.get('kind', ''))
		if kind_filter and kind_filter not in kind:
			continue
		out.append(
			ReviewFinding(
				id=f'{source}_{kind}_{len(out)}',
				category=category,
				severity=str(issue.get('severity', 'advisory')),
				message=str(issue.get('detail', kind)),
				rationale=f'Visual insight detected {kind}',
				recommendation=str(issue.get('recommendation', '')),
				source=source,
				selector=issue.get('selector'),
				affected_element=issue.get('selector') or issue.get('tag'),
				evidence=f'visual_insight kind={kind} detail={issue.get("detail", "")}',
				confidence=0.92 if issue.get('severity') == 'blocking' else 0.78,
				confirmed=True,
			)
		)
	return out
