"""Build MCP tool responses with inline images for host agents."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

VISUAL_ATTACHMENTS_KEY = '_visual_attachments'


def visual_uris_for_scan(scan_id: str, obs: dict[str, Any]) -> dict[str, str | None]:
	"""Stable resource URIs for scan artifacts."""
	base = f'perception://scan/{scan_id}'
	out: dict[str, str | None] = {
		'screenshot_uri': None,
		'annotated_screenshot_uri': None,
		'crop_screenshot_uri': None,
	}
	if obs.get('screenshot_path'):
		out['screenshot_uri'] = f'{base}/screenshot.png'
	if obs.get('annotated_screenshot_path'):
		out['annotated_screenshot_uri'] = f'{base}/screenshot-annotated.png'
	if obs.get('crop_screenshot_path'):
		out['crop_screenshot_uri'] = f'{base}/screenshot-crop.png'
	return out


def attach_visual_paths(
	envelope: dict[str, Any],
	paths: list[tuple[str, str]],
) -> dict[str, Any]:
	"""Register filesystem paths to inline as MCP images (stripped from JSON output)."""
	if not paths:
		return envelope
	existing = list(envelope.get(VISUAL_ATTACHMENTS_KEY) or [])
	for label, path in paths:
		if path and Path(path).is_file():
			existing.append({'label': label, 'path': path, 'mime': 'image/png'})
	envelope[VISUAL_ATTACHMENTS_KEY] = existing
	return envelope


def _preferred_image_paths(obs: dict[str, Any]) -> list[tuple[str, str]]:
	"""Order: annotated first (most useful), then crop, then raw viewport."""
	paths: list[tuple[str, str]] = []
	ann = obs.get('annotated_screenshot_path')
	crop = obs.get('crop_screenshot_path')
	raw = obs.get('screenshot_path')
	if ann:
		paths.append(('annotated_viewport', str(ann)))
	if crop:
		paths.append(('element_crop', str(crop)))
	if raw and str(raw) != str(ann):
		paths.append(('viewport', str(raw)))
	return paths


def attach_observation_visuals(envelope: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
	return attach_visual_paths(envelope, _preferred_image_paths(obs))


def attach_diff_visuals(envelope: dict[str, Any], visual_diff: dict[str, Any]) -> dict[str, Any]:
	paths: list[tuple[str, str]] = []
	if visual_diff.get('side_by_side_path'):
		paths.append(('diff_side_by_side', str(visual_diff['side_by_side_path'])))
	if visual_diff.get('heatmap_path'):
		paths.append(('diff_heatmap', str(visual_diff['heatmap_path'])))
	return attach_visual_paths(envelope, paths)


def envelope_for_json(envelope: dict[str, Any]) -> dict[str, Any]:
	"""Copy envelope without internal attachment list."""
	out = dict(envelope)
	out.pop(VISUAL_ATTACHMENTS_KEY, None)
	return out


def envelope_to_mcp_contents(result: dict[str, Any], mcp_types: Any) -> list[Any]:
	"""Text JSON envelope + inline PNG images for the host model."""
	attachments = list(result.get(VISUAL_ATTACHMENTS_KEY) or [])
	payload = envelope_for_json(result)
	contents: list[Any] = [
		mcp_types.TextContent(type='text', text=json.dumps(payload, indent=2, default=str)),
	]
	seen: set[str] = set()
	for item in attachments:
		path = str(item.get('path') or '')
		if not path or path in seen:
			continue
		seen.add(path)
		p = Path(path)
		if not p.is_file():
			continue
		label = str(item.get('label') or 'screenshot')
		mime = str(item.get('mime') or 'image/png')
		data_b64 = base64.b64encode(p.read_bytes()).decode('ascii')
		contents.append(
			mcp_types.ImageContent(type='image', data=data_b64, mimeType=mime),
		)
		# Small caption so agents know which image is which
		contents.append(mcp_types.TextContent(type='text', text=f'[perception image: {label}]'))
	return contents
