"""Crit / Rams architecture patterns — specialist orchestration methodology.

Borrowed patterns:
- Multiple specialist reviewers (not one monolithic prompt)
- Per-specialist findings with category tags
- Coordinator merges, dedupes, assigns severity
- Recommendation generation from aggregated issues
"""
from __future__ import annotations

from ...models import ProviderContribution, ReviewRequest


class CritRamsMethodologyProvider:
	name = 'crit_rams'
	kind = 'methodology'
	lane = 'subjective'

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		# Methodology marker — actual specialist execution is in reviewers/coordinator
		return ProviderContribution(
			provider=self.name,
			notes=[
				'crit_rams: specialist-review architecture active via ReviewCoordinator',
				'severity_assignment: coordinator merges specialist outputs',
			],
			degraded=['crit_rams_methodology_marker'],
		)
