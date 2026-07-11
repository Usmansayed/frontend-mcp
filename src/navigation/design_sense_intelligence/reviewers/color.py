"""Color specialist reviewer — reasons over ColorSnapshot, not raw CSS."""
from __future__ import annotations

from ..models import ReviewFinding, ReviewRequest
from ..snapshot_access import resolve_snapshot


class ColorReviewer:
	name = 'color_reviewer'
	category = 'color'
	lane = 'objective'

	async def review(self, request: ReviewRequest) -> list[ReviewFinding]:
		snapshot = resolve_snapshot(request)
		if snapshot is not None:
			findings: list[ReviewFinding] = []
			for i, fail in enumerate(snapshot.colors.wcag_failures[:8]):
				ratio = fail.get('ratio', 0)
				tag = fail.get('tag', 'element')
				fg = fail.get('foreground', '')
				bg = fail.get('background', '')
				findings.append(
					ReviewFinding(
						id=f'color_wcag_{i}',
						category='color',
						severity='major' if ratio < 3 else 'minor',
						message=f'{tag} text contrast is {ratio}:1, below WCAG AA (4.5:1)',
						rationale='Measured from computed foreground/background colors',
						recommendation=(
							f'Increase foreground contrast or darken background for {tag}. '
							f'Current: {fg} on {bg}.'
						),
						source=self.name,
						selector=tag,
						affected_element=tag,
						evidence=f'contrast_matrix ratio={ratio} fg={fg} bg={bg}',
						confidence=0.95,
						confirmed=True,
						metadata={'ratio': ratio, 'required': 4.5},
					)
				)
			if snapshot.colors.raw_color_count > 0 and not findings:
				findings.append(
					ReviewFinding(
						id='color_raw_values',
						category='color',
						severity='minor',
						message=f'{snapshot.colors.raw_color_count} elements use non-token colors',
						rationale='Computed styles contain raw hex/rgb values outside design tokens',
						recommendation='Map colors to design tokens',
						source=self.name,
						evidence=f'raw_color_count={snapshot.colors.raw_color_count}',
						confidence=0.8,
						confirmed=True,
					)
				)
			if findings:
				return findings

		return []
