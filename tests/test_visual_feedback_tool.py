"""Common visual-feedback tool tests (no live browser).

Covers the purpose-shaped policy (pack defaults, feedback extras, next_actions
routing) and the perception_visual_feedback handler (LOOK phase schema/prompt,
judgment round-trip, offline scan reuse, input validation).
"""
from __future__ import annotations

import asyncio
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.mcp.visual_feedback_handlers import handle_visual_feedback
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_feedback_policy import (
	build_purpose_next_actions,
	normalize_purpose_feedback,
	purpose_feedback_schema,
	purpose_for_tool,
	purpose_recommended_resource,
	purpose_screenshot_pack,
	resolve_purpose,
)
from navigation.visual_browser_intelligence.visual.visual_response import VISUAL_ATTACHMENTS_KEY


def _png_path(td: str) -> str:
	from PIL import Image

	buf = io.BytesIO()
	Image.new('RGB', (400, 300), (250, 250, 250)).save(buf, format='PNG')
	p = Path(td) / 'shot.png'
	p.write_bytes(buf.getvalue())
	return str(p)


# ---------------------------------------------------------------- policy


def test_resolve_purpose() -> None:
	assert resolve_purpose({'purpose': 'inspiration'}) == 'inspiration'
	assert resolve_purpose({'purpose': 'DESIGN'}) == 'design'
	assert resolve_purpose({'purpose': 'nonsense'}) == 'general'
	assert resolve_purpose({}) == 'general'


def test_purpose_for_tool_aliases() -> None:
	assert purpose_for_tool('perception_consistency_review') == 'consistency'
	assert purpose_for_tool('perception_consistency_audit') == 'consistency'
	assert purpose_for_tool('perception_design_review') == 'design'
	assert purpose_for_tool('perception_build_design_snapshot') == 'design'


def test_purpose_pack_defaults() -> None:
	assert purpose_screenshot_pack('design', {}) == 'design'
	assert purpose_screenshot_pack('consistency', {}) == 'design'
	assert purpose_screenshot_pack('inspiration', {}) == 'full'
	assert purpose_screenshot_pack('forms', {}) == 'section'
	assert purpose_screenshot_pack('component', {}) == 'viewport'
	assert purpose_screenshot_pack('hotfix', {}) == 'viewport'
	assert purpose_screenshot_pack('general', {}) == 'viewport'


def test_purpose_pack_overrides() -> None:
	# Explicit pack wins over purpose default.
	assert purpose_screenshot_pack('design', {'screenshot_pack': 'viewport'}) == 'viewport'
	# Selector forces element.
	assert purpose_screenshot_pack('design', {'screenshot_selector': '#hero'}) == 'element'
	# Focused sections narrow to section pack.
	assert purpose_screenshot_pack('general', {'focus_sections': ['header']}) == 'section'
	# include_screenshots=false disables capture.
	assert purpose_screenshot_pack('design', {'include_screenshots': False}) == 'none'


def test_purpose_schema_and_resource() -> None:
	for purpose in ('design', 'consistency', 'component', 'inspiration', 'hotfix', 'forms', 'general'):
		schema = purpose_feedback_schema(purpose)
		assert 'judgment' in schema and 'notes' in schema, purpose
		assert purpose_recommended_resource(purpose).startswith('perception://'), purpose
	assert 'borrow' in purpose_feedback_schema('inspiration')
	assert 'standard_hints' in purpose_feedback_schema('consistency')
	assert 'field_issues' in purpose_feedback_schema('forms')


def test_normalize_purpose_feedback_extras() -> None:
	fb = normalize_purpose_feedback(
		{
			'visual_feedback': {
				'judgment': 'needs_work',
				'notes': 'hero is flat',
				'borrow': ['split hero'],
				'ignore': ['dark theme'],
			}
		},
		'inspiration',
	)
	assert fb is not None
	assert fb['purpose'] == 'inspiration'
	assert fb['borrow'] == ['split hero']
	assert fb['ignore'] == ['dark theme']

	fb = normalize_purpose_feedback(
		{'visual_feedback': {'judgment': 'needs_work', 'standard_hints': ['std.nav.gap']}},
		'consistency',
	)
	assert fb is not None and fb['standard_hints'] == ['std.nav.gap']

	# Extras from other purposes are not picked up.
	fb = normalize_purpose_feedback(
		{'visual_feedback': {'judgment': 'needs_work', 'borrow': ['x']}},
		'design',
	)
	assert fb is not None and 'borrow' not in fb

	assert normalize_purpose_feedback({}, 'design') is None


def _env(session_id: str = 'sess-1', scan_id: str = 'scan-1') -> dict:
	return {
		'ok': True,
		'session_id': session_id,
		'scan_id': scan_id,
		'data': {'agent_summary': {'advisory': []}},
	}


def test_purpose_next_actions_routing() -> None:
	# ok → done ladder only, no purpose extras.
	acts = build_purpose_next_actions(
		purpose='inspiration',
		tool='perception_visual_feedback',
		envelope=_env(),
		feedback={'judgment': 'ok', 'notes': '', 'focus_sections': [], 'focus_selector': None, 'issues': []},
	)
	assert [a['action'] for a in acts] == ['continue_done_ladder']

	base_fb = {'judgment': 'needs_work', 'notes': '', 'focus_sections': [], 'focus_selector': None, 'issues': []}

	acts = build_purpose_next_actions(
		purpose='inspiration', tool='perception_visual_feedback', envelope=_env(),
		feedback={**base_fb, 'borrow': ['split hero']},
	)
	assert any(a['action'] == 'collect_inspiration' for a in acts), acts

	acts = build_purpose_next_actions(
		purpose='forms', tool='perception_visual_feedback', envelope=_env(), feedback=dict(base_fb),
	)
	assert any(a['action'] == 'probe_form' for a in acts), acts

	acts = build_purpose_next_actions(
		purpose='hotfix', tool='perception_visual_feedback', envelope=_env(), feedback=dict(base_fb),
	)
	assert any(a['action'] == 'diff_after_fix' for a in acts), acts

	acts = build_purpose_next_actions(
		purpose='component', tool='perception_visual_feedback', envelope=_env(), feedback=dict(base_fb),
	)
	assert any(a['action'] == 'select_component_foundation' for a in acts), acts

	acts = build_purpose_next_actions(
		purpose='consistency', tool='perception_visual_feedback', envelope=_env(),
		feedback={**base_fb, 'standard_hints': ['std.nav.gap']},
	)
	fix = [a for a in acts if a['action'] == 'propose_consistency_fix']
	assert fix and fix[0]['args_hint']['standard_id'] == 'std.nav.gap', acts


# ---------------------------------------------------------------- handler


async def _handler_requires_target() -> None:
	out = await handle_visual_feedback(SessionStore(), ScanRegistry(), SnapshotRegistry(), {})
	assert out['ok'] is False
	assert 'session_id' in str(out['error'])


async def _handler_look_phase_offline() -> None:
	with tempfile.TemporaryDirectory() as td:
		scans = ScanRegistry()
		rec = scans.register(
			session_id='sess-1',
			run_id='run-1',
			url='http://localhost/',
			observation={'url': 'http://localhost/', 'screenshot_path': _png_path(td)},
		)
		out = await handle_visual_feedback(
			SessionStore(),
			scans,
			SnapshotRegistry(),
			{'scan_id': rec.scan_id, 'purpose': 'forms'},
		)
		assert out['ok'] is True, out
		data = out['data']
		assert data['purpose'] == 'forms'
		assert data['recommended_resource'].startswith('perception://')
		# LOOK phase (no judgment yet): schema + prompt tell the agent what to fill.
		assert 'field_issues' in data['feedback_schema']
		assert 'forms' in data['feedback_prompt']
		assert 'next_actions' not in data
		# Offline: stored screenshot reused and attached.
		atts = out.get(VISUAL_ATTACHMENTS_KEY) or []
		assert any(a['label'] == 'reference_screenshot' for a in atts), atts
		assert data.get('visual_evidence'), data
		adv = data['agent_summary']['advisory']
		assert any('LOOK phase' in str(a) for a in adv), adv


async def _handler_judgment_round_trip() -> None:
	with tempfile.TemporaryDirectory() as td:
		scans = ScanRegistry()
		rec = scans.register(
			session_id='sess-1',
			run_id='run-1',
			url='http://localhost/',
			observation={'url': 'http://localhost/', 'screenshot_path': _png_path(td)},
		)
		out = await handle_visual_feedback(
			SessionStore(),
			scans,
			SnapshotRegistry(),
			{
				'scan_id': rec.scan_id,
				'purpose': 'inspiration',
				'visual_feedback': {
					'judgment': 'needs_work',
					'notes': 'hero lacks focal point',
					'borrow': ['oversized display type'],
				},
			},
		)
		assert out['ok'] is True, out
		data = out['data']
		fb = data['visual_feedback']
		assert fb['purpose'] == 'inspiration'
		assert fb['borrow'] == ['oversized display type']
		actions = [a['action'] for a in data['next_actions']]
		assert 'collect_inspiration' in actions, actions
		# Judgment phase replaces the LOOK-phase schema prompt.
		assert 'feedback_schema' not in data


async def _handler_feedback_only_no_capture() -> None:
	out = await handle_visual_feedback(
		SessionStore(),
		ScanRegistry(),
		SnapshotRegistry(),
		{
			'session_id': 'sess-x',
			'purpose': 'hotfix',
			'include_screenshots': False,
			'visual_judgment': 'needs_work',
			'visual_notes': 'button overlaps footer',
		},
	)
	assert out['ok'] is True, out
	data = out['data']
	assert data['purpose'] == 'hotfix'
	assert not out.get(VISUAL_ATTACHMENTS_KEY)
	actions = [a['action'] for a in data['next_actions']]
	assert 'diff_after_fix' in actions, actions


def test_handler_requires_target() -> None:
	asyncio.run(_handler_requires_target())


def test_handler_look_phase_offline() -> None:
	asyncio.run(_handler_look_phase_offline())


def test_handler_judgment_round_trip() -> None:
	asyncio.run(_handler_judgment_round_trip())


def test_handler_feedback_only_no_capture() -> None:
	asyncio.run(_handler_feedback_only_no_capture())


def main() -> None:
	test_resolve_purpose()
	test_purpose_for_tool_aliases()
	test_purpose_pack_defaults()
	test_purpose_pack_overrides()
	test_purpose_schema_and_resource()
	test_normalize_purpose_feedback_extras()
	test_purpose_next_actions_routing()
	test_handler_requires_target()
	test_handler_look_phase_offline()
	test_handler_judgment_round_trip()
	test_handler_feedback_only_no_capture()
	print('visual feedback tool tests passed')


if __name__ == '__main__':
	main()
