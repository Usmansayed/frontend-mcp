"""Official Figma REST API loader — post-duplication deep extraction."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from navigation.figma_intelligence.adapters.ecosystem import to_design_snapshot_payload
from navigation.figma_intelligence.community_duplication.models import OfficialFilePayload
from navigation.figma_intelligence.models import FigmaExtractionResult

FIGMA_API_BASE = 'https://api.figma.com'


class FigmaRestClient:
	"""Thin client for official Figma REST API using PAT."""

	def __init__(self, pat: str) -> None:
		self._pat = pat.strip()

	def available(self) -> bool:
		return bool(self._pat)

	def request(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
		if not self.available():
			raise RuntimeError('figma_pat_missing')
		url = FIGMA_API_BASE + path
		if params:
			url += '?' + urllib.parse.urlencode(params)
		req = urllib.request.Request(
			url,
			headers={'X-Figma-Token': self._pat, 'Accept': 'application/json'},
		)
		try:
			with urllib.request.urlopen(req, timeout=90) as resp:
				return json.loads(resp.read().decode('utf-8'))
		except urllib.error.HTTPError as exc:
			body = exc.read().decode('utf-8', 'replace')[:500]
			raise RuntimeError(f'figma_api_http_{exc.code}:{body}') from exc

	def get_file(self, file_key: str, *, depth: int | None = None) -> dict[str, Any]:
		params: dict[str, str] = {}
		if depth is not None:
			params['depth'] = str(depth)
		return self.request(f'/v1/files/{file_key}', params=params or None)

	def get_local_variables(self, file_key: str) -> dict[str, Any]:
		return self.request(f'/v1/files/{file_key}/variables/local')

	def get_file_styles(self, file_key: str) -> dict[str, Any]:
		# Styles ship inside GET /v1/files/{key} — dedicated endpoint not required.
		data = self.get_file(file_key, depth=1)
		return {'meta': data.get('styles', {}), 'status': 200}

	@staticmethod
	def pat_from_env() -> str:
		return (
			os.environ.get('FIGMA_ACCESS_TOKEN', '').strip()
			or os.environ.get('figma_pat', '').strip()
			or os.environ.get('FIGMA_PAT', '').strip()
		)


def load_official_file(file_key: str, *, pat: str) -> OfficialFilePayload:
	"""Fetch document tree, components, styles, variables via official REST."""
	client = FigmaRestClient(pat)
	degraded: list[str] = []

	file_data = client.get_file(file_key)
	metadata = {
		'name': file_data.get('name'),
		'lastModified': file_data.get('lastModified'),
		'version': file_data.get('version'),
		'thumbnailUrl': file_data.get('thumbnailUrl'),
		'editorType': file_data.get('editorType'),
	}

	variables: dict[str, Any] = {}
	try:
		variables = client.get_local_variables(file_key)
	except Exception as exc:
		degraded.append(f'variables_unavailable:{type(exc).__name__}')

	components = file_data.get('components') or {}
	if not isinstance(components, dict):
		components = {}
	styles = file_data.get('styles') or {}
	if not isinstance(styles, dict):
		styles = {}

	return OfficialFilePayload(
		file_key=file_key,
		document=file_data.get('document') or {},
		components=components,
		styles=styles,
		variables=variables,
		metadata=metadata,
		degraded=degraded,
	)


def official_to_extraction(
	official: OfficialFilePayload,
	*,
	candidate_id: str,
) -> FigmaExtractionResult:
	"""Map official REST payload → FigmaExtractionResult."""
	var_meta = official.variables.get('meta', official.variables) if official.variables else {}
	var_collections = []
	if isinstance(var_meta, dict):
		var_collections = list((var_meta.get('variableCollections') or {}).values())

	components_list = [
		{'id': k, **v} if isinstance(v, dict) else {'id': k, 'value': v}
		for k, v in official.components.items()
	]
	styles_list = [
		{'id': k, **v} if isinstance(v, dict) else {'id': k, 'value': v}
		for k, v in official.styles.items()
	]

	auto_layout_nodes = _collect_auto_layout(official.document)

	return FigmaExtractionResult(
		candidate_id=candidate_id,
		provider_id='official_figma_rest',
		raw_payload={
			'file_key': official.file_key,
			'metadata': official.metadata,
			'document': official.document,
			'variables': official.variables,
			'auto_layout_nodes': auto_layout_nodes,
		},
		tokens=styles_list,
		components=components_list,
		variables=var_collections if var_collections else _variables_as_list(official.variables),
		patterns=auto_layout_nodes,
		degraded=list(official.degraded),
	)


def build_design_snapshot(extraction: FigmaExtractionResult) -> dict[str, Any]:
	"""Produce Design Snapshot compatible payload from official extraction."""
	base = to_design_snapshot_payload(extraction)
	base['file_key'] = extraction.raw_payload.get('file_key', '')
	base['metadata'] = extraction.raw_payload.get('metadata', {})
	base['document'] = extraction.raw_payload.get('document', {})
	base['auto_layout_nodes'] = extraction.raw_payload.get('auto_layout_nodes', [])
	base['source_stage'] = 'community_duplication_pipeline'
	return base


def _variables_as_list(variables: dict[str, Any]) -> list[dict[str, Any]]:
	if not variables:
		return []
	meta = variables.get('meta', variables)
	if not isinstance(meta, dict):
		return []
	out: list[dict[str, Any]] = []
	for coll in (meta.get('variableCollections') or {}).values():
		if isinstance(coll, dict):
			out.append(coll)
	return out


def _collect_auto_layout(node: dict[str, Any], acc: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
	items = acc if acc is not None else []
	if not isinstance(node, dict):
		return items
	if node.get('layoutMode') in {'HORIZONTAL', 'VERTICAL'}:
		items.append({
			'id': node.get('id'),
			'name': node.get('name'),
			'layoutMode': node.get('layoutMode'),
			'itemSpacing': node.get('itemSpacing'),
			'paddingLeft': node.get('paddingLeft'),
			'paddingRight': node.get('paddingRight'),
			'paddingTop': node.get('paddingTop'),
			'paddingBottom': node.get('paddingBottom'),
		})
	for child in node.get('children') or []:
		if isinstance(child, dict):
			_collect_auto_layout(child, items)
	return items
