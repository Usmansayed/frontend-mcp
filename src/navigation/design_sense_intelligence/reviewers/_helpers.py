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
				source=source,
			)
		)
	return out
