"""Persistent Resource Graph — provider knowledge + asset metadata (never copyrighted files)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef

DEFAULT_GRAPH_PATH = Path(os.environ.get('RESOURCE_GRAPH_PATH', '.cache/resource_graph.json'))


class ResourceGraphStore:
	def __init__(self, *, path: Path | None = None) -> None:
		self._path = path or DEFAULT_GRAPH_PATH
		self._data: dict[str, Any] | None = None

	def load(self) -> dict[str, Any]:
		if self._data is not None:
			return self._data
		if self._path.is_file():
			try:
				self._data = json.loads(self._path.read_text(encoding='utf-8'))
				return self._data
			except json.JSONDecodeError:
				pass
		self._data = self._empty_graph()
		return self._data

	def save(self) -> None:
		data = self.load()
		data['updated_at'] = time.time()
		self._path.parent.mkdir(parents=True, exist_ok=True)
		self._path.write_text(json.dumps(data, indent=2), encoding='utf-8')

	def _empty_graph(self) -> dict[str, Any]:
		return {
			'version': 1,
			'updated_at': time.time(),
			'providers': {pid: meta.to_dict() for pid, meta in SEED_PROVIDERS.items()},
			'assets': {},
			'selections': [],
		}

	def upsert_asset(self, asset: ResourceAssetRef) -> None:
		data = self.load()
		assets: dict[str, Any] = data.setdefault('assets', {})
		assets[asset.resource_id] = {
			'resource_id': asset.resource_id,
			'provider_id': asset.provider_id,
			'category': asset.category.value,
			'title': asset.title,
			'tags': list(asset.tags),
			'style': list(asset.style),
			'format': asset.format,
			'license': asset.license.to_dict() if asset.license else None,
			'metadata': dict(asset.metadata),
			'indexed_at': time.time(),
		}

	def record_selection(self, selection: dict[str, Any]) -> None:
		data = self.load()
		history: list[dict[str, Any]] = data.setdefault('selections', [])
		history.append({**selection, 'recorded_at': time.time()})
		data['selections'] = history[-100:]

	def get_provider(self, provider_id: str) -> dict[str, Any] | None:
		return self.load().get('providers', {}).get(provider_id)

	def summary(self) -> dict[str, Any]:
		data = self.load()
		return {
			'provider_count': len(data.get('providers') or {}),
			'asset_count': len(data.get('assets') or {}),
			'selection_count': len(data.get('selections') or []),
			'updated_at': data.get('updated_at'),
			'path': str(self._path),
		}
