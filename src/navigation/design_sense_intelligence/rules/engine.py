"""Design Lint rule engine for browser DOM/CSS targets."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import ReviewFinding, ReviewRequest
from .context import LintContext
from .implementations import evaluate_all


@dataclass(slots=True)
class LintResult:
	findings: list[ReviewFinding] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)


def run_lint(request: ReviewRequest) -> LintResult:
	ctx = LintContext.from_request(request)
	if not ctx.elements:
		return LintResult(
			degraded=['design_lint_no_computed_styles'],
		)
	findings = evaluate_all(ctx)
	degraded = ['design_lint_deterministic'] if findings else ['design_lint_clean']
	return LintResult(findings=findings, degraded=degraded)
