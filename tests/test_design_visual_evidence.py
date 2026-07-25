"""Design/consistency visual-evidence attachment tests (no live browser).

Covers the post-hook that inlines viewport/full/section screenshots on design and
consistency tool envelopes so the agent reasons on rendered pixels, not code alone.
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

import navigation.visual_browser_intelligence.visual.visual_capture as vc
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.mcp.design_intelligence_handlers import attach_design_visuals
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_response import VISUAL_ATTACHMENTS_KEY


def _png_bytes(w: int = 1200, h: int = 2000) -> bytes:
	from PIL import Image

	buf = io.BytesIO()
	Image.new('RGB', (w, h), (250, 250, 250)).save(buf, format='PNG')
	return buf.getvalue()


class _FakeSession:
	"""Minimal browser-use session stand-in returning a real PNG for any screenshot."""

	def __init__(self) -> None:
		self.calls: list[tuple[bool, dict | None]] = []

	async def take_screenshot(self, full_page: bool = False, clip: dict | None = None) -> bytes:
		self.calls.append((full_page, clip))
		return _png_bytes()


async def _capture_design_evidence_pack() -> None:
	async def _no_insights(_session: object) -> None:
		return None

	orig = vc.collect_visual_insights
	vc.collect_visual_insights = _no_insights  # avoid DOM insight round-trips
	try:
		with tempfile.TemporaryDirectory() as td:
			# Layout regions use w/h keys (element clips use width/height) — cover both.
			regions = [
				{'role': 'header', 'label': 'header', 'rect': {'x': 0, 'y': 0, 'w': 1200, 'h': 100}},
				{'role': 'main', 'label': 'main', 'rect': {'x': 0, 'y': 100, 'width': 1200, 'height': 900}},
			]
			paths, _degraded = await vc.capture_design_evidence(
				_FakeSession(), Path(td), 'unit', regions=regions, max_sections=2,
			)
			labels = [label for label, _ in paths]
			assert any(label in ('viewport', 'viewport_annotated') for label in labels), labels
			assert 'full_page' in labels, labels
			assert any(label.startswith('section:') for label in labels), labels
			for _label, path in paths:
				assert Path(path).is_file(), path
	finally:
		vc.collect_visual_insights = orig


async def _attach_design_visuals_offline_reference() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture({'url': 'http://localhost/', 'elements': []})
	with tempfile.TemporaryDirectory() as td:
		ref = Path(td) / 'ref.png'
		ref.write_bytes(_png_bytes(400, 300))
		snap_dict = snapshot.to_dict()
		snap_dict.setdefault('provenance', {})['screenshot_ref'] = str(ref)
		snapshots = SnapshotRegistry()
		rec = snapshots.register(snapshot=snap_dict, url=snapshot.url)

		envelope = {
			'ok': True,
			'tool': 'perception_design_review',
			'data': {'snapshot_id': rec.snapshot_id, 'agent_summary': {'advisory': []}},
		}
		out = await attach_design_visuals(
			envelope,
			store=SessionStore(),
			scans=ScanRegistry(),
			snapshots=snapshots,
			arguments={'snapshot_id': rec.snapshot_id},
			tool='perception_design_review',
		)
		atts = out.get(VISUAL_ATTACHMENTS_KEY) or []
		assert any(a['label'] == 'reference_screenshot' for a in atts), atts
		assert out['data'].get('visual_evidence'), out['data']
		adv = out['data']['agent_summary']['advisory']
		assert any('VISUAL EVIDENCE' in str(a) for a in adv), adv


async def _attach_design_visuals_disabled() -> None:
	envelope = {'ok': True, 'data': {}}
	out = await attach_design_visuals(
		envelope,
		store=SessionStore(),
		scans=ScanRegistry(),
		snapshots=SnapshotRegistry(),
		arguments={'include_screenshots': False},
		tool='perception_design_review',
	)
	assert VISUAL_ATTACHMENTS_KEY not in out


async def _attach_design_visuals_feedback_next_actions() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture({'url': 'http://localhost/', 'elements': []})
	with tempfile.TemporaryDirectory() as td:
		ref = Path(td) / 'ref.png'
		ref.write_bytes(_png_bytes(400, 300))
		snap_dict = snapshot.to_dict()
		snap_dict.setdefault('provenance', {})['screenshot_ref'] = str(ref)
		snapshots = SnapshotRegistry()
		rec = snapshots.register(snapshot=snap_dict, url=snapshot.url)

		envelope = {
			'ok': True,
			'session_id': 'sess_fb',
			'tool': 'perception_design_review',
			'data': {
				'snapshot_id': rec.snapshot_id,
				'agent_summary': {'advisory': []},
				'findings': [
					{
						'standard_id': 'std.nav.gap',
						'selector': 'header',
						'detail': 'header gap too tight',
					}
				],
			},
		}
		out = await attach_design_visuals(
			envelope,
			store=SessionStore(),
			scans=ScanRegistry(),
			snapshots=snapshots,
			arguments={
				'snapshot_id': rec.snapshot_id,
				'visual_feedback': {
					'judgment': 'needs_work',
					'notes': 'header too dense',
					'focus_sections': ['header'],
				},
			},
			tool='perception_design_review',
		)
		assert out['data'].get('visual_feedback', {}).get('judgment') == 'needs_work'
		actions = out['data'].get('next_actions') or []
		assert actions, out['data']
		kinds = [a['action'] for a in actions]
		assert 'verify_section' in kinds or 'edit_then_remeasure' in kinds
		assert out['data'].get('agent_summary', {}).get('next_actions')


async def _attach_design_visuals_never_raises_on_bad_envelope() -> None:
	out = await attach_design_visuals(
		{'ok': False, 'error': 'boom'},
		store=SessionStore(),
		scans=ScanRegistry(),
		snapshots=SnapshotRegistry(),
		arguments={},
		tool='perception_consistency_audit',
	)
	assert out['ok'] is False
	assert VISUAL_ATTACHMENTS_KEY not in out


def test_capture_design_evidence_pack() -> None:
	asyncio.run(_capture_design_evidence_pack())


def test_attach_design_visuals_offline_reference() -> None:
	asyncio.run(_attach_design_visuals_offline_reference())


def test_attach_design_visuals_disabled() -> None:
	asyncio.run(_attach_design_visuals_disabled())


def test_attach_design_visuals_feedback_next_actions() -> None:
	asyncio.run(_attach_design_visuals_feedback_next_actions())


def test_attach_design_visuals_never_raises_on_bad_envelope() -> None:
	asyncio.run(_attach_design_visuals_never_raises_on_bad_envelope())


def main() -> int:
	test_capture_design_evidence_pack()
	test_attach_design_visuals_offline_reference()
	test_attach_design_visuals_disabled()
	test_attach_design_visuals_feedback_next_actions()
	test_attach_design_visuals_never_raises_on_bad_envelope()
	print('design visual evidence: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
