"""Typography specialist reviewer — reasons over TypographySnapshot."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ..snapshot_access import resolve_snapshot
from ._helpers import findings_from_visual_insights


class TypographyReviewer:
	name = 'typography_reviewer'
	category = 'typography'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		snapshot = resolve_snapshot(request)
		if snapshot is not None:
			findings: list[ReviewFinding] = []
			for i, issue in enumerate(snapshot.typography.issues[:10]):
				kind = str(issue.get('kind', 'typography issue'))
				findings.append(
					ReviewFinding(
						id=f'typography_snapshot_{i}',
						category='typography',
						severity=str(issue.get('severity', 'minor')),
						message=str(issue.get('detail', kind)),
						rationale=f'Typography snapshot detected {kind}',
						source=self.name,
						evidence=f'typography kind={kind} detail={issue.get("detail", "")}',
						affected_element=issue.get('selector') or issue.get('tag'),
						confidence=0.82,
						confirmed=True,
					)
				)
			if not snapshot.typography.scale_on_grid and snapshot.typography.font_sizes_px:
				sizes = snapshot.typography.font_sizes_px[:6]
				findings.append(
					ReviewFinding(
						id='typography_off_scale',
						category='typography',
						severity='minor',
						message='Type scale includes sizes off project typography grid',
						rationale='Font sizes do not align with declared typography token scale',
						recommendation='Normalize font sizes to design token scale',
						source=self.name,
						evidence=f'font_sizes_px={sizes}',
						confidence=0.8,
						confirmed=True,
					)
				)
			if findings:
				return findings

		return findings_from_visual_insights(
			request, category='typography', source=self.name, kind_filter='truncat'
		)
