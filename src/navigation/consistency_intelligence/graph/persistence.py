"""Project Design Graph persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ProjectDesignGraph, empty_graph

DEFAULT_RELATIVE_PATH = Path('.perception') / 'design_graph.json'
HISTORY_DIR = Path('.perception') / 'history'
MAX_HISTORY_VERSIONS = 20


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


class GraphStore:
	"""Load/save Project Design Graph per project."""

	def __init__(self, *, storage_root: Path | None = None) -> None:
		self._storage_root = storage_root
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
