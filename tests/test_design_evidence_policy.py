"""Unit tests for screenshot pack policy + visual feedback → next_actions."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.visual_browser_intelligence.visual.design_evidence_policy import (
	PACK_DESIGN,
	PACK_ELEMENT,
	PACK_NONE,
	PACK_SECTION,
	build_visual_next_actions,
	normalize_visual_feedback,
	pack_capture_kwargs,
	resolve_screenshot_pack,
)


def test_resolve_pack_defaults_to_design_for_consistency() -> None:
	assert (
		resolve_screenshot_pack('perception_consistency_audit', {}) == PACK_DESIGN
	)
	assert resolve_screenshot_pack('perception_design_review', {}) == PACK_DESIGN
	assert (
		resolve_screenshot_pack(
			'perception_design_review', {'include_screenshots': False}
		)
		== PACK_NONE
	)


def test_feedback_narrows_pack_to_section_or_element() -> None:
	fb = normalize_visual_feedback(
		{'visual_feedback': {'judgment': 'needs_work', 'focus_sections': ['header']}}
	)
	assert fb is not None
	assert resolve_screenshot_pack('perception_design_review', {}, feedback=fb) == PACK_SECTION

	fb2 = normalize_visual_feedback({'screenshot_selector': 'nav.primary'})
	assert (
		resolve_screenshot_pack('perception_consistency_review', {}, feedback=fb2)
		== PACK_ELEMENT
	)


def test_normalize_pulls_sections_from_notes() -> None:
	fb = normalize_visual_feedback(
		{'visual_notes': 'the header is too dense and footer is cramped', 'visual_judgment': 'needs_work'}
	)
	assert fb is not None
	assert fb['judgment'] == 'needs_work'
	assert 'header' in fb['focus_sections']
	assert 'footer' in fb['focus_sections']


def test_next_actions_from_feedback_and_findings() -> None:
	fb = normalize_visual_feedback(
		{
			'visual_feedback': {
				'judgment': 'needs_work',
				'notes': 'header spacing',
				'focus_sections': ['header'],
				'issues': [
					{
						'section': 'header',
						'problem': 'too dense',
						'wanted': 'more padding',
					}
				],
			}
		}
	)
	assert fb is not None
	envelope = {
		'ok': True,
		'session_id': 'sess_x',
		'scan_id': 'scan_x',
		'data': {
			'snapshot_id': 'snap_x',
			'findings': [
				{
					'standard_id': 'std.button.padding',
					'selector': 'button.primary',
					'detail': 'padding off scale header spacing',
					'actual': {'padding': '4px'},
				}
			],
		},
	}
	actions = build_visual_next_actions(
		tool='perception_consistency_audit', envelope=envelope, feedback=fb
	)
	kinds = [a['action'] for a in actions]
	assert 'verify_section' in kinds
	assert 'edit_then_remeasure' in kinds
	assert 'propose_consistency_fix' in kinds
	# Top actions should carry session hints.
	assert any(a.get('args_hint', {}).get('session_id') == 'sess_x' for a in actions)


def test_judgment_ok_advances_done_ladder() -> None:
	fb = normalize_visual_feedback({'visual_judgment': 'ok'})
	assert fb is not None
	actions = build_visual_next_actions(
		tool='perception_design_review',
		envelope={'ok': True, 'session_id': 's', 'data': {}},
		feedback=fb,
	)
	assert actions[0]['action'] == 'continue_done_ladder'


def test_pack_capture_kwargs_section_prefers_full_for_crops() -> None:
	kw = pack_capture_kwargs(
		PACK_SECTION,
		{'max_sections': 2},
		{'focus_sections': ['footer'], 'focus_selector': None},
	)
	assert kw['want_viewport'] is True
	assert kw['want_full'] is True  # needed to crop sections
	assert kw['want_sections'] is True
	assert kw['prefer_sections'] == ['footer']
	assert kw['max_sections'] == 2


def main() -> int:
	test_resolve_pack_defaults_to_design_for_consistency()
	test_feedback_narrows_pack_to_section_or_element()
	test_normalize_pulls_sections_from_notes()
	test_next_actions_from_feedback_and_findings()
	test_judgment_ok_advances_done_ladder()
	test_pack_capture_kwargs_section_prefers_full_for_crops()
	print('design evidence policy: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
