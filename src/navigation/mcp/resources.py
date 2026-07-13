"""MCP resources — guides, evals, and scan artifacts."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from navigation.core.paths import (
	agent_guide_path,
	module_doc,
	validation_form_eval_path,
)
from navigation.core.scan_registry import ScanRegistry

_SCAN_ARTIFACTS: dict[str, str] = {
	'report.json': 'application/json',
	'diagnosis.json': 'application/json',
	'diagnosis.md': 'text/markdown',
	'screenshot.png': 'image/png',
	'screenshot-annotated.png': 'image/png',
	'screenshot-crop.png': 'image/png',
	'network.har': 'application/json',
}


_STATIC_GUIDE_CACHE: dict[str, tuple[str, str]] = {}


def _read_md(path: Path, label: str) -> tuple[str, str, bool]:
	if not path.is_file():
		raise FileNotFoundError(f'{label} not found at {path}')
	return 'text/markdown', path.read_text(encoding='utf-8'), False


def _artifact_from_report(obs: dict[str, Any], kind: str) -> Path | None:
	pr = obs.get('perception_report') or {}
	for art in pr.get('artifacts') or []:
		if art.get('kind') == kind:
			path = Path(str(art.get('path') or ''))
			if path.is_file():
				return path
	return None


def _scan_artifact_path(rec: object, artifact: str) -> Path | None:
	obs = getattr(rec, 'observation', {}) or {}
	if artifact == 'report.json':
		return None
	if artifact == 'diagnosis.json':
		return _artifact_from_report(obs, 'diagnosis_json')
	if artifact == 'diagnosis.md':
		return _artifact_from_report(obs, 'diagnosis_md')
	if artifact == 'screenshot.png':
		raw = obs.get('screenshot_path')
		return Path(str(raw)) if raw else None
	if artifact == 'screenshot-annotated.png':
		raw = obs.get('annotated_screenshot_path')
		return Path(str(raw)) if raw else None
	if artifact == 'screenshot-crop.png':
		raw = obs.get('crop_screenshot_path')
		return Path(str(raw)) if raw else None
	if artifact == 'network.har':
		net = obs.get('network') or {}
		raw = net.get('har_path')
		return Path(str(raw)) if raw else None
	return None


def list_resources(scans: ScanRegistry | None = None) -> list[dict[str, str]]:
	resources = [
		{
			'uri': 'perception://agent-guide',
			'name': 'AGENT_GUIDE',
			'description': 'Primary behavior contract — playbooks for host agent (read at session start)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://inspiration-guide',
			'name': 'INSPIRATION_AGENT_GUIDE',
			'description': 'Inspiration Intelligence — per-site navigation, preview URLs, anti-bot (read before inspiration tools)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://resource-guide',
			'name': 'RESOURCE_AGENT_GUIDE',
			'description': 'Resource Intelligence — icons, avatars, license rules, ephemeral preview blobs (read before resource tools)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://resolver-guide',
			'name': 'RESOLVER_AGENT_GUIDE',
			'description': 'Resolver Intelligence — fast route/component/token lookup (read before resolve_* tools)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://seo-guide',
			'name': 'SEO_AGENT_GUIDE',
			'description': 'SEO Intelligence — free-first SEO orchestration, providers, verify loop (read before seo tools)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://figma-guide',
			'name': 'FIGMA_AGENT_GUIDE',
			'description': 'Figma Intelligence — PAT connect, normalized design context (read before figma tools)',
			'mimeType': 'text/markdown',
		},
		{
			'uri': 'perception://eval/validation-form',
			'name': 'Validation Form Eval',
			'description': 'M3 eval scenario — complete using AGENT_GUIDE §4 form playbook',
			'mimeType': 'text/markdown',
		},
	]
	if scans is not None:
		for rec in scans.all():
			resources.append(
				{
					'uri': f'perception://scan/{rec.scan_id}/report.json',
					'name': f'scan_report_{rec.scan_id}',
					'description': f'Observation report for {rec.scan_id}',
					'mimeType': 'application/json',
				}
			)
			for artifact, mime in _SCAN_ARTIFACTS.items():
				if artifact == 'report.json':
					continue
				path = _scan_artifact_path(rec, artifact)
				if path is not None and path.is_file():
					resources.append(
						{
							'uri': f'perception://scan/{rec.scan_id}/{artifact}',
							'name': f'scan_{artifact.replace(".", "_")}_{rec.scan_id}',
							'description': f'{artifact} for {rec.scan_id}',
							'mimeType': mime,
						}
					)
			net = (rec.observation or {}).get('network') or {}
			if net.get('har_path'):
				har_uri = f'perception://scan/{rec.scan_id}/network.har'
				if not any(r.get('uri') == har_uri for r in resources):
					resources.append(
						{
							'uri': har_uri,
							'name': f'scan_network_har_{rec.scan_id}',
							'description': f'network.har for {rec.scan_id}',
							'mimeType': 'application/json',
						}
					)
	return resources


def _cached_guide(uri: str, path: Path, label: str) -> tuple[str, str, bool]:
	if uri in _STATIC_GUIDE_CACHE:
		mime, text = _STATIC_GUIDE_CACHE[uri]
		return mime, text, False
	mime, text, is_blob = _read_md(path, label)
	if not is_blob:
		_STATIC_GUIDE_CACHE[uri] = (mime, text)
	return mime, text, is_blob


def read_resource(uri: str, scans: ScanRegistry | None = None) -> tuple[str, str, bool]:
	"""Return (mime_type, payload, is_blob). Raises KeyError if unknown."""
	if uri == 'perception://agent-guide':
		return _cached_guide(uri, agent_guide_path(), 'AGENT_GUIDE.md')

	if uri == 'perception://inspiration-guide':
		return _cached_guide(
			uri,
			module_doc('inspiration_intelligence', 'docs', 'INSPIRATION_AGENT_GUIDE.md'),
			'INSPIRATION_AGENT_GUIDE.md',
		)

	if uri == 'perception://resource-guide':
		return _cached_guide(
			uri,
			module_doc('resource_intelligence', 'docs', 'RESOURCE_AGENT_GUIDE.md'),
			'RESOURCE_AGENT_GUIDE.md',
		)

	if uri == 'perception://resolver-guide':
		return _cached_guide(
			uri,
			module_doc('resolver_intelligence', 'docs', 'RESOLVER_AGENT_GUIDE.md'),
			'RESOLVER_AGENT_GUIDE.md',
		)

	if uri == 'perception://seo-guide':
		return _cached_guide(
			uri,
			module_doc('seo_intelligence', 'docs', 'SEO_AGENT_GUIDE.md'),
			'SEO_AGENT_GUIDE.md',
		)

	if uri == 'perception://figma-guide':
		return _cached_guide(
			uri,
			module_doc('figma_intelligence', 'docs', 'FIGMA_AGENT_GUIDE.md'),
			'FIGMA_AGENT_GUIDE.md',
		)

	if uri == 'perception://eval/validation-form':
		return _cached_guide(uri, validation_form_eval_path(), 'VALIDATION_FORM_EVAL.md')

	if uri.startswith('perception://scan/') and scans is not None:
		parts = uri.split('/')
		if len(parts) >= 5:
			scan_id = parts[3]
			artifact = parts[4]
			rec = scans.get(scan_id)
			if rec is None:
				raise KeyError(uri)
			if artifact == 'report.json':
				payload = dict(rec.observation)
				if rec.observation.get('perception_report'):
					payload['perception_report'] = rec.observation['perception_report']
				return 'application/json', json.dumps(payload, indent=2, default=str), False
			if artifact == 'diagnosis.json':
				pr = rec.observation.get('perception_report') or {}
				return 'application/json', json.dumps(pr, indent=2, default=str), False
			if artifact == 'diagnosis.md':
				file_path = _scan_artifact_path(rec, artifact)
				if file_path is None or not file_path.is_file():
					raise KeyError(uri)
				return 'text/markdown', file_path.read_text(encoding='utf-8'), False
			if artifact in _SCAN_ARTIFACTS and artifact != 'report.json':
				file_path = _scan_artifact_path(rec, artifact)
				if file_path is None or not file_path.is_file():
					return 'text/plain', '', False
				if _SCAN_ARTIFACTS[artifact] == 'application/json':
					return 'application/json', file_path.read_text(encoding='utf-8'), False
				raw = file_path.read_bytes()
				return _SCAN_ARTIFACTS[artifact], base64.b64encode(raw).decode('ascii'), True

	raise KeyError(uri)
