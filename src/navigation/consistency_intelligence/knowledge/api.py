"""Knowledge API — query router."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.consistency_intelligence.graph.model import ProjectDesignGraph
from navigation.consistency_intelligence.graph.persistence import GraphStore

from .envelope import KnowledgeQuery, KnowledgeResponse, stub_response
from .queries import ALL_HANDLERS
from .registry import QUERY_BY_ID, QUERY_CATALOG


class KnowledgeAPI:
	"""Query interface for Project Design Graph — all consumers use this."""

	def __init__(self, store: GraphStore | None = None) -> None:
		self._store = store or GraphStore()
		self._handlers = dict(ALL_HANDLERS)

	def list_queries(self) -> list[dict[str, Any]]:
		return [
			{
				'query_id': spec.query_id,
				'description': spec.description,
				'category': spec.category,
				'params': list(spec.params),
				'phase': spec.phase,
			}
			for spec in QUERY_CATALOG
		]

	def load_graph(
		self,
		project_id: str = 'default',
		*,
		repo_root: str | Path | None = None,
	) -> ProjectDesignGraph:
		root = Path(repo_root) if repo_root else None
		if root is not None:
			self._store = GraphStore(storage_root=root)
		return self._store.load(project_id, repo_root=str(repo_root or ''))

	def save_graph(self, graph: ProjectDesignGraph) -> str | None:
		path = self._store.save(graph)
		return str(path) if path else None

	def query(
		self,
		query_id: str,
		params: dict[str, Any] | None = None,
		*,
		project_id: str = 'default',
		repo_root: str | Path | None = None,
	) -> KnowledgeResponse:
		spec = QUERY_BY_ID.get(query_id)
		if spec is None:
			graph = self.load_graph(project_id, repo_root=repo_root)
			q = KnowledgeQuery(query_id=query_id, params=dict(params or {}))
			resp = stub_response(graph, q, message=f'Unknown query_id: {query_id}')
			resp.degraded.append('unknown_query_id')
			return resp

		graph = self.load_graph(project_id, repo_root=repo_root)
		q = KnowledgeQuery(query_id=query_id, params=dict(params or {}))
		handler = self._handlers.get(query_id)
		if handler is None:
			return stub_response(graph, q, message=f'Handler not registered for `{query_id}`.')

		return handler(graph, q)

	def summary(
		self,
		*,
		project_id: str = 'default',
		repo_root: str | Path | None = None,
	) -> KnowledgeResponse:
		return self.query('graph.summary', {}, project_id=project_id, repo_root=repo_root)

	def graph_stats(self, graph: ProjectDesignGraph) -> dict[str, Any]:
		return self._store.summary_stats(graph)
