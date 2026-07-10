"""Tests for Design Sense Intelligence architecture."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.design_sense_intelligence import DesignSenseService, ReviewRequest
from navigation.design_sense_intelligence.rules.engine import run_lint
from navigation.design_sense_intelligence.reviewers.coordinator import ReviewCoordinator


def test_design_lint_rules_on_computed_styles() -> None:
	request = ReviewRequest(
		computed_styles=[
			{
				'selector': 'button.primary',
				'tag': 'button',
				'style': {
					'color': '#ff0000',
					'backgroundColor': '#00ff00',
					'fontSize': '13px',
					'padding': '10px',
					'borderRadius': '5px',
				},
				'classes': [],
			}
		],
	)
	result = run_lint(request)
	assert result.findings
	assert any(f.source == 'design_lint' for f in result.findings)


async def test_coordinator_runs_specialists_and_providers() -> None:
	coordinator = ReviewCoordinator()
	report = await coordinator.run(
		ReviewRequest(
			user_task='Complete checkout',
			visual_insights={
				'issues': [{'kind': 'horizontal_overflow', 'severity': 'blocking', 'detail': 'overflow'}],
				'blocking': ['horizontal_overflow'],
			},
		)
	)
	assert report.consulted_reviewers
	assert report.consulted_providers
	assert 'layout_reviewer' in report.consulted_reviewers
	assert 'open_design' in report.consulted_providers
	assert 'design_knowledge' in report.consulted_providers
	assert report.reasoning is not None
	assert report.reasoning.narrative
	assert report.objective_findings or report.subjective_findings
	assert report.workflow_phases


async def test_service_review_facade() -> None:
	service = DesignSenseService()
	report = await service.review(ReviewRequest(user_task='Sign in'))
	assert isinstance(report.summary, str)
	assert report.findings or report.degraded


def main() -> int:
	test_design_lint_rules_on_computed_styles()
	asyncio.run(test_coordinator_runs_specialists_and_providers())
	asyncio.run(test_service_review_facade())
	print('design sense intelligence: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
