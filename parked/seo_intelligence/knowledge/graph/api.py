"""SEO Knowledge Graph query API — read-only agent interface."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.seo_intelligence.knowledge.graph.queries import list_graph_queries, run_graph_query
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore


class SeoGraphAPI:
	def __init__(self, store: SeoKnowledgeGraphStore | None = None) -> None:
		self._store = store or SeoKnowledgeGraphStore()

	@classmethod
	def for_path(cls, path: str | Path) -> SeoGraphAPI:
		return cls(SeoKnowledgeGraphStore(path=Path(path)))

	def list_queries(self) -> list[dict[str, Any]]:
		return list_graph_queries()

	def query(self, query_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
		return run_graph_query(self._store, query_id, params)

	def summary(self) -> dict[str, Any]:
		return self.query('graph.summary')
