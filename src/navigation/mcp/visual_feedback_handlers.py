"""Common visual feedback: one LOOK → judge → act loop for every intelligence.

``perception_visual_feedback`` is the shared entry point: it captures the right
screenshot pack for a *purpose* (design / consistency / component / inspiration /
hotfix / forms / general), attaches the images inline, tells the agent which
feedback JSON to fill, and — when the agent returns judgment — emits advisory
``next_actions``. The design/consistency tools reuse the same runner as thin
aliases, so there is exactly one capture/feedback code path.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from navigation.core.envelope import make_envelope
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_response import attach_visual_paths

TOOL_VISUAL_FEEDBACK = 'perception_visual_feedback'


def _stored_screenshot_ref(
	scans: ScanRegistry,
	scan_id: str,
	snapshot: DesignSnapshot | None,
) -> str | None:
	"""Fallback screenshot for offline (snapshot_id / scan_id) calls."""
	if scan_id:
		rec = scans.get(scan_id)
		obs = getattr(rec, 'observation', None) if rec else None
		if isinstance(obs, dict):
			ref = obs.get('annotated_screenshot_path') or obs.get('screenshot_path')
			if ref and Path(str(ref)).is_file():
				return str(ref)
	if snapshot is not None:
		prov = getattr(snapshot, 'provenance', None) or {}
		ref = prov.get('screenshot_ref')
		if ref and Path(str(ref)).is_file():
			return str(ref)
	return None


async def _capture_or_reuse_visuals(
	*,
	store: SessionStore,
	scans: ScanRegistry,
	session_id: str,
	snapshot: DesignSnapshot | None,
	arguments: dict[str, Any],
	tool: str,
	scan_id: str,
	live_ok: bool,
	pack_kwargs: dict[str, Any] | None = None,
) -> list[tuple[str, str]]:
	"""Live-capture a design-evidence pack, else reuse a stored screenshot. Best-effort."""
	from navigation.visual_browser_intelligence.visual.visual_capture import (
		capture_design_evidence,
	)

	paths: list[tuple[str, str]] = []
	rec = None
	if live_ok and session_id:
		try:
			rec = await store.ensure(session_id)
		except Exception:
			rec = None
	if rec is not None and getattr(rec, 'browser', None) is not None:
		try:
			regions = list((snapshot.layout.regions if snapshot and snapshot.layout else None) or [])
			kwargs = dict(pack_kwargs or {})
			# Back-compat if caller did not resolve pack.
			if not kwargs:
				selector = str(arguments.get('screenshot_selector') or '').strip() or None
				try:
					max_sections = int(arguments.get('max_sections', 3))
				except (TypeError, ValueError):
					max_sections = 3
				kwargs = {
					'want_viewport': True,
					'want_full': True,
					'want_sections': True,
					'want_element': bool(selector),
					'selector': selector,
					'max_sections': max_sections,
					'prefer_sections': [],
				}
			try:
				timeout_s = float(arguments.get('screenshot_timeout_s', 25.0))
			except (TypeError, ValueError):
				timeout_s = 25.0
			paths, _deg = await asyncio.wait_for(
				capture_design_evidence(
					rec.browser,
					rec.artifacts_dir / 'images',
					f"{tool.replace('perception_', '')}-{uuid.uuid4().hex[:8]}",
					regions=regions,
					selector=kwargs.get('selector'),
					max_sections=int(kwargs.get('max_sections') or 0),
					prefer_sections=list(kwargs.get('prefer_sections') or []),
					want_viewport=bool(kwargs.get('want_viewport', True)),
					want_full=bool(kwargs.get('want_full', True)),
					want_sections=bool(kwargs.get('want_sections', True)),
					want_element=bool(kwargs.get('want_element', True)),
				),
				timeout=timeout_s,
			)
		except Exception:
			paths = []
	if not paths:
		ref = _stored_screenshot_ref(scans, scan_id, snapshot)
		if ref:
			paths = [('reference_screenshot', ref)]
	return paths


def _resolve_snapshot(
	snapshots: SnapshotRegistry,
	*,
	snapshot_id: str,
	scan_id: str,
	data: dict[str, Any],
) -> tuple[DesignSnapshot | None, Any]:
	snapshot: DesignSnapshot | None = None
	rec = snapshots.get(snapshot_id) if snapshot_id else None
	if rec is None and scan_id:
		rec = snapshots.get_by_scan(scan_id)
	if rec is not None:
		try:
			snapshot = DesignSnapshot.from_dict(rec.snapshot)
		except Exception:
			snapshot = None
	if snapshot is None and isinstance(data.get('snapshot'), dict):
		try:
			snapshot = DesignSnapshot.from_dict(data['snapshot'])
		except Exception:
			snapshot = None
	return snapshot, rec


def _apply_feedback(
	envelope: dict[str, Any],
	*,
	purpose: str,
	tool: str,
	feedback: dict[str, Any],
) -> None:
	from navigation.visual_browser_intelligence.visual.visual_feedback_policy import (
		build_purpose_next_actions,
	)
	from navigation.visual_browser_intelligence.visual.design_evidence_policy import (
		visual_feedback_advisory,
	)

	next_actions = build_purpose_next_actions(
		purpose=purpose, tool=tool, envelope=envelope, feedback=feedback
	)
	envelope['data']['visual_feedback'] = feedback
	envelope['data']['next_actions'] = next_actions
	summ = envelope['data'].setdefault('agent_summary', {})
	if isinstance(summ, dict):
		summ['visual_feedback'] = feedback
		summ['next_actions'] = next_actions
		adv = summ.setdefault('advisory', [])
		if isinstance(adv, list):
			adv.extend(visual_feedback_advisory(feedback, next_actions))


async def run_visual_feedback(
	envelope: dict[str, Any],
	*,
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
	tool: str,
	purpose: str,
) -> dict[str, Any]:
	"""Shared runner: capture-or-reuse pack, attach images, shape the feedback loop.

	Used by the common ``perception_visual_feedback`` tool and (as thin aliases)
	by the design/consistency post-hooks. Never raises — visuals are best-effort
	enrichment, the underlying tool result must survive any capture failure.
	"""
	try:
		from navigation.visual_browser_intelligence.visual.design_evidence_policy import (
			PACK_NONE,
		)
		from navigation.visual_browser_intelligence.visual.visual_feedback_policy import (
			normalize_purpose_feedback,
			purpose_feedback_prompt,
			purpose_feedback_schema,
			purpose_pack_capture_kwargs,
			purpose_recommended_resource,
			purpose_screenshot_pack,
		)

		if not isinstance(envelope, dict) or not envelope.get('ok'):
			return envelope
		if not isinstance(envelope.get('data'), dict):
			envelope['data'] = {}

		envelope['data']['purpose'] = purpose
		envelope['data']['recommended_resource'] = purpose_recommended_resource(purpose)

		feedback = normalize_purpose_feedback(arguments, purpose)
		pack = purpose_screenshot_pack(purpose, arguments, feedback=feedback)
		if pack == PACK_NONE:
			# Still record feedback → next_actions even without new captures.
			if feedback:
				_apply_feedback(envelope, purpose=purpose, tool=tool, feedback=feedback)
			return envelope

		data = envelope['data']
		snapshot_id = str(data.get('snapshot_id') or arguments.get('snapshot_id') or '').strip()
		scan_id = str(
			envelope.get('scan_id') or data.get('scan_id') or arguments.get('scan_id') or ''
		).strip()
		snapshot, rec = _resolve_snapshot(
			snapshots, snapshot_id=snapshot_id, scan_id=scan_id, data=data
		)
		session_id = str(
			envelope.get('session_id')
			or arguments.get('session_id')
			or (rec.session_id if rec else '')
			or ''
		).strip()
		snapshot_id_only = bool(arguments.get('snapshot_id')) and not (
			arguments.get('session_id') or arguments.get('scan_id')
		)

		pack_kwargs = purpose_pack_capture_kwargs(pack, arguments, feedback)
		paths = await _capture_or_reuse_visuals(
			store=store,
			scans=scans,
			session_id=session_id,
			snapshot=snapshot,
			arguments=arguments,
			tool=tool,
			scan_id=scan_id,
			live_ok=not snapshot_id_only,
			pack_kwargs=pack_kwargs,
		)
		if paths:
			attach_visual_paths(envelope, paths)
			data['visual_evidence'] = [
				{'label': label, 'path': path} for label, path in paths
			]
			data['screenshot_pack'] = pack
			summ = data.setdefault('agent_summary', {})
			if isinstance(summ, dict):
				summ['visual_evidence'] = [label for label, _ in paths]
				summ['screenshot_pack'] = pack
				adv = summ.setdefault('advisory', [])
				if isinstance(adv, list):
					adv.append(
						f'VISUAL EVIDENCE attached (pack={pack}: '
						+ ', '.join(label for label, _ in paths)
						+ '). LOOK at the images and drive changes from appearance, not code alone.'
					)

		if feedback:
			_apply_feedback(envelope, purpose=purpose, tool=tool, feedback=feedback)
		else:
			# LOOK phase: tell the agent exactly what JSON to fill for this purpose.
			data['feedback_schema'] = purpose_feedback_schema(purpose)
			data['feedback_prompt'] = purpose_feedback_prompt(purpose)
			summ = data.setdefault('agent_summary', {})
			if isinstance(summ, dict):
				adv = summ.setdefault('advisory', [])
				if isinstance(adv, list):
					adv.append(
						f'LOOK phase (purpose={purpose}) — fill visual_feedback per '
						'feedback_schema and call this tool again to get next_actions.'
					)
	except Exception:
		return envelope
	return envelope


async def handle_visual_feedback(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	"""Common tool: LOOK pack + purpose-shaped judgment round-trip."""
	from navigation.visual_browser_intelligence.visual.visual_feedback_policy import (
		resolve_purpose,
	)

	session_id = str(arguments.get('session_id') or '').strip()
	scan_id = str(arguments.get('scan_id') or '').strip()
	if not session_id and not scan_id:
		return make_envelope(
			TOOL_VISUAL_FEEDBACK,
			ok=False,
			error='session_id (live capture) or scan_id (stored screenshot) required',
		)

	purpose = resolve_purpose(arguments)
	url = ''
	if scan_id:
		rec = scans.get(scan_id)
		url = str(getattr(rec, 'url', '') or '') if rec else ''

	envelope = make_envelope(
		TOOL_VISUAL_FEEDBACK,
		ok=True,
		session_id=session_id or None,
		scan_id=scan_id or None,
		url=url,
		data={'agent_summary': {'advisory': []}},
	)
	return await run_visual_feedback(
		envelope,
		store=store,
		scans=scans,
		snapshots=snapshots,
		arguments=arguments,
		tool=TOOL_VISUAL_FEEDBACK,
		purpose=purpose,
	)
