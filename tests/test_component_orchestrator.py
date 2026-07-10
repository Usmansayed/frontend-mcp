"""Unit tests for synthesis-based foundation selection (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.component_intelligence.integration_models import (
	CodebaseGuidance,
	ConsistencyGuidance,
	DesignSenseGuidance,
	FrameworkGuidance,
)
from navigation.component_intelligence.models import ComponentCandidate
from navigation.component_intelligence.selection.filter import filter_candidates
from navigation.component_intelligence.guidance.synthesis import rank_key, synthesize_guidance


def _candidate(name: str, score: float) -> ComponentCandidate:
	return ComponentCandidate(
		id=f'shadcn_ecosystem:shadcn:{name}',
		provider='shadcn_ecosystem',
		provider_group='shadcn_ecosystem',
		name=name,
		title=name,
		category='component',
		description='',
		relevance_score=score,
	)


def test_filter_candidates_caps_and_dedupes() -> None:
	items = [_candidate('input', 0.9), _candidate('input', 0.8), _candidate('card', 0.5)]
	out = filter_candidates(items, max_count=2)
	assert len(out) == 2
	assert out[0].name == 'input'


def test_synthesis_ineligible_when_framework_blocks() -> None:
	fw = FrameworkGuidance(compatible=False, issues=['react_version_mismatch'])
	result = synthesize_guidance(
		_candidate('x', 0.9),
		fw,
		CodebaseGuidance(),
		DesignSenseGuidance(),
		ConsistencyGuidance(),
	)
	assert not result.eligible


def test_synthesis_prefers_fewer_issues_in_rank_key() -> None:
	from navigation.component_intelligence.integration_models import CandidateGuidance

	def _guidance(issue_count: int, relevance: float) -> CandidateGuidance:
		fw = FrameworkGuidance(compatible=True, issues=['x'] * issue_count)
		syn = synthesize_guidance(_candidate('a', relevance), fw, CodebaseGuidance(), DesignSenseGuidance(), ConsistencyGuidance())
		return CandidateGuidance('id', fw, CodebaseGuidance(), DesignSenseGuidance(), ConsistencyGuidance(), syn)

	good = _guidance(0, 0.5)
	bad = _guidance(3, 0.9)
	assert rank_key(_candidate('a', 0.5), good) < rank_key(_candidate('a', 0.9), bad)


def main() -> int:
	test_filter_candidates_caps_and_dedupes()
	test_synthesis_ineligible_when_framework_blocks()
	test_synthesis_prefers_fewer_issues_in_rank_key()
	print('component orchestrator: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
