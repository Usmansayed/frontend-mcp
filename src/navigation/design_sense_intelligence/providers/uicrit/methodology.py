"""UICrit methodology — critique pipeline and rubric (research reproduction, not their model).

Pipeline stages:
1. Contextualize (task + screen scope)
2. Generate critiques (separate from localization)
3. Score rubric dimensions (aesthetics, learnability, efficiency, overall)
4. Aggregate overall quality from dimension scores

Critique categories from UICrit: layout, color contrast, text readability,
button usability, learnability.
"""
from __future__ import annotations

from ...models import DimensionScore, ProviderContribution, ReviewFinding, ReviewRequest
from ...workflows.uicrit_pipeline import UICRIT_DIMENSIONS, run_uicrit_pipeline


class UICritMethodologyProvider:
	name = 'uicrit'
	kind = 'methodology'
	lane = 'subjective'

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		result = run_uicrit_pipeline(request)
		return ProviderContribution(
			provider=self.name,
			findings=result['findings'],
			scores=result['scores'],
			notes=result['notes'],
			degraded=result['degraded'],
		)
