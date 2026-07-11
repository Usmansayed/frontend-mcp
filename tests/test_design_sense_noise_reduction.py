"""Tests for noise-reduction pipeline: placeholders, debate, confidence, evidence."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.design_sense_intelligence.confidence.engine import ConfidenceContext, compute_confidence
from navigation.design_sense_intelligence.debate.engine import ReviewerDebateEngine
from navigation.design_sense_intelligence.evidence.policy import enforce_evidence_policy
from navigation.design_sense_intelligence.filters.placeholders import drop_placeholders, is_placeholder_finding
from navigation.design_sense_intelligence.models import ReviewFinding, ReviewRequest


def test_placeholder_detection() -> None:
	assert is_placeholder_finding(
		ReviewFinding(id='x', category='color', severity='advisory', message='Verify: Contrast ratio compliant')
	)
	assert is_placeholder_finding(
		ReviewFinding(
			id='ms_tokens_unknown',
			category='tokens',
			severity='minor',
			message='Design tokens not supplied — cannot verify token compliance',
		)
	)
	assert not is_placeholder_finding(
		ReviewFinding(
			id='color_wcag_0',
			category='color',
			severity='major',
			message='button text contrast is 2.1:1, below WCAG AA (4.5:1)',
			evidence='ratio=2.1',
			rationale='Measured contrast',
			affected_element='button',
		)
	)


def test_drop_placeholders() -> None:
	findings = [
		ReviewFinding(id='a', category='x', severity='advisory', message='Verify: something'),
		ReviewFinding(
			id='b',
			category='color',
			severity='major',
			message='Low contrast',
			evidence='ratio=2.0',
			rationale='bad',
			affected_element='btn',
		),
	]
	kept, dropped = drop_placeholders(findings)
	assert dropped == 1
	assert len(kept) == 1


def test_confidence_scoring() -> None:
	f = ReviewFinding(
		id='lint',
		category='tokens',
		severity='minor',
		message='Color not from design token',
		evidence='button.primary color uses raw value #ff0000',
		rationale='Token compliance',
		recommendation='Use token',
		affected_element='button.primary',
		confirmed=True,
	)
	score = compute_confidence(f, ConfidenceContext(has_snapshot=True))
	assert score >= 0.55


def test_debate_removes_unsubstantiated_contrast() -> None:
	engine = ReviewerDebateEngine()
	findings = [
		ReviewFinding(
			id='color_guess',
			category='color',
			severity='minor',
			message='Possible contrast issue on body text',
			source='color_reviewer',
		),
	]
	result = engine.run(findings)
	assert result.removed_count == 1


def test_evidence_policy_drops_advisory_without_proof() -> None:
	findings = [
		ReviewFinding(
			id='advisory',
			category='ux',
			severity='advisory',
			message='Support learning by doing',
			rationale='heuristic',
		),
		ReviewFinding(
			id='real',
			category='layout',
			severity='blocking',
			message='Horizontal overflow',
			evidence='scrollWidth=2400 viewport=1280',
			rationale='Page wider than viewport',
			affected_element='body',
		),
	]
	kept = enforce_evidence_policy(findings, request=ReviewRequest(user_task='test'))
	assert len(kept) == 1
	assert kept[0].id == 'real'


def main() -> int:
	test_placeholder_detection()
	test_drop_placeholders()
	test_confidence_scoring()
	test_debate_removes_unsubstantiated_contrast()
	test_evidence_policy_drops_advisory_without_proof()
	print('design sense noise reduction: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
