"""Design Lint methodology — rule taxonomy ported for DOM/CSS (not Figma integration).

Studied from destefanis/design-lint: determineType → per-layer rule sets
(checkType, checkFills, checkStrokes, checkEffects, checkRadius, custom rules).
Our engine lives in design_sense_intelligence/rules/ and feeds Consistency Intelligence later.
"""
from __future__ import annotations

from ...models import ProviderContribution, ReviewRequest
from ...rules.engine import run_lint


class DesignLintMethodologyProvider:
	name = 'design_lint'
	kind = 'methodology'
	lane = 'objective'

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		result = run_lint(request)
		return ProviderContribution(
			provider=self.name,
			findings=result.findings,
			notes=['Design Lint rule engine (DOM/CSS port) — deterministic validation'],
			degraded=result.degraded,
		)
