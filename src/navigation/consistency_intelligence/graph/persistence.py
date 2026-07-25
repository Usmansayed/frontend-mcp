"""Project Design Graph persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ProjectDesignGraph, empty_graph

DEFAULT_RELATIVE_PATH = Path('.perception') / 'design_graph.json'
HISTORY_DIR = Path('.perception') / 'history'
MAX_HISTORY_VERSIONS = 20

# Process-wide stores so refresh → summary across separate service instances still see data.
_PROCESS_STORES: dict[str, "GraphStore"] = {}
# project_id → last storage root that successfully loaded/saved a non-empty graph
_LAST_GRAPH_ROOTS: dict[str, str] = {}


def graph_summary_stats(graph: ProjectDesignGraph) -> dict[str, Any]:
	return {
		'project_id': graph.meta.project_id,
		'graph_version': graph.meta.graph_version,
		'component_count': len(graph.components),
		'pattern_count': len(graph.patterns),
		'standard_count': len(graph.foundations.standards) + sum(
			len(c.standards) for c in graph.components.values()
		),
		'token_count': len(graph.foundations.color_tokens),
		'exception_count': len(graph.exceptions),
		'relationship_count': len(graph.relationships),
		'overall_confidence': graph.confidence.overall,
	}


def remember_graph_root(project_id: str, storage_root: Path | str | None) -> None:
	"""Record the storage root used for a successful refresh so summary can reuse it."""
	if storage_root is None:
		return
	try:
		_LAST_GRAPH_ROOTS[str(project_id or 'default')] = str(Path(storage_root).resolve())
	except OSError:
		_LAST_GRAPH_ROOTS[str(project_id or 'default')] = str(storage_root)


def last_graph_root(project_id: str = 'default') -> str | None:
	return _LAST_GRAPH_ROOTS.get(str(project_id or 'default'))


def find_populated_graph_root(project_id: str = 'default') -> str | None:
	"""Prefer a process store that already has components/standards for this project."""
	pid = str(project_id or 'default')
	remembered = last_graph_root(pid)
	if remembered:
		return remembered
	best: tuple[int, str] | None = None
	for key, store in _PROCESS_STORES.items():
		if key == '__memory__':
			continue
		try:
			graph = store.load(pid)
		except Exception:
			continue
		stats = graph_summary_stats(graph)
		score = int(stats.get('component_count') or 0) + int(stats.get('standard_count') or 0)
		if score <= 0:
			continue
		if best is None or score > best[0]:
			best = (score, key)
	return best[1] if best else None


def _store_key(storage_root: Path | None) -> str:
	if storage_root is None:
		return '__memory__'
	try:
		return str(Path(storage_root).resolve())
	except OSError:
		return str(storage_root)


def get_graph_store(storage_root: Path | None = None) -> "GraphStore":
	"""Return the process-scoped GraphStore for this storage root."""
	key = _store_key(Path(storage_root) if storage_root is not None else None)
	store = _PROCESS_STORES.get(key)
	if store is None:
		root = Path(storage_root) if storage_root is not None else None
		store = GraphStore(storage_root=root)
		_PROCESS_STORES[key] = store
	return store


def clear_process_graph_stores() -> None:
	"""Test helper — drop process-wide graph caches."""
	for store in list(_PROCESS_STORES.values()):
		store.clear_cache()
	_PROCESS_STORES.clear()
	_LAST_GRAPH_ROOTS.clear()


class GraphStore:
	"""Load/save Project Design Graph per project."""

	def __init__(self, *, storage_root: Path | None = None) -> None:
		self._storage_root = Path(storage_root) if storage_root is not None else None
		self._cache: dict[str, ProjectDesignGraph] = {}

	def _graph_path(self, project_id: str) -> Path | None:
		if self._storage_root is None:
			return None
		if project_id == 'default':
			return self._storage_root / DEFAULT_RELATIVE_PATH
		safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project_id)
		return self._storage_root / '.perception' / f'design_graph_{safe}.json'

	def load(self, project_id: str = 'default', *, repo_root: str = '') -> ProjectDesignGraph:
		if project_id in self._cache:
			return self._cache[project_id]

		path = self._graph_path(project_id)
		if path is not None and path.is_file():
			data = json.loads(path.read_text(encoding='utf-8'))
			graph = ProjectDesignGraph.from_dict(data)
			self._cache[project_id] = graph
			return graph

		graph = empty_graph(project_id, repo_root=repo_root)
		self._cache[project_id] = graph
		return graph

	def _history_dir(self, project_id: str) -> Path | None:
		if self._storage_root is None:
			return None
		safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project_id)
		return self._storage_root / HISTORY_DIR / safe

	def save(self, graph: ProjectDesignGraph) -> Path | None:
		project_id = graph.meta.project_id
		self._cache[project_id] = graph
		path = self._graph_path(project_id)
		if path is None:
			return None
		path.parent.mkdir(parents=True, exist_ok=True)
		payload = json.dumps(graph.to_dict(), indent=2)
		path.write_text(payload, encoding='utf-8')
		self._archive_version(graph)
		return path

	def _archive_version(self, graph: ProjectDesignGraph) -> None:
		hdir = self._history_dir(graph.meta.project_id)
		if hdir is None or not graph.meta.graph_version:
			return
		hdir.mkdir(parents=True, exist_ok=True)
		safe_ver = graph.meta.graph_version.replace(':', '-')
		hist_path = hdir / f'{safe_ver}.json'
		hist_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding='utf-8')
		versions = sorted(hdir.glob('*.json'), key=lambda p: p.stat().st_mtime)
		while len(versions) > MAX_HISTORY_VERSIONS:
			versions.pop(0).unlink(missing_ok=True)

	def list_versions(self, project_id: str = 'default') -> list[str]:
		hdir = self._history_dir(project_id)
		if hdir is None or not hdir.is_dir():
			return []
		return sorted(p.stem for p in hdir.glob('*.json'))

	def load_version(self, project_id: str, version: str) -> ProjectDesignGraph | None:
		hdir = self._history_dir(project_id)
		if hdir is None or not hdir.is_dir():
			return None
		safe = version.replace(':', '-')
		candidate = hdir / f'{safe}.json'
		if not candidate.is_file():
			for path in hdir.glob('*.json'):
				if path.stem == safe or path.stem.endswith(version.split('.')[-1]):
					candidate = path
					break
			else:
				return None
		data = json.loads(candidate.read_text(encoding='utf-8'))
		return ProjectDesignGraph.from_dict(data)

	@property
	def storage_root(self) -> Path | None:
		return self._storage_root

	def clear_cache(self) -> None:
		self._cache.clear()

	def summary_stats(self, graph: ProjectDesignGraph) -> dict[str, Any]:
		return graph_summary_stats(graph)
