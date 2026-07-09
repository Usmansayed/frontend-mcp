from __future__ import annotations

from typing import Any

from .interface import GraphQueryResult, ICodeGraph


class NullCodeGraph(ICodeGraph):
    """Safe fallback when CRG is unavailable."""

    def _disabled(self, action: str) -> GraphQueryResult:
        return GraphQueryResult(
            ok=False,
            source="null",
            summary=f"Code graph unavailable: {action} skipped.",
            error="code_graph_unavailable",
        )

    def initialize(self) -> GraphQueryResult:
        return self._disabled("initialize")

    def refresh(self) -> GraphQueryResult:
        return self._disabled("refresh")

    def rebuild(self) -> GraphQueryResult:
        return self._disabled("rebuild")

    def search(self, query: str, *, kind: str | None = None, limit: int = 20) -> GraphQueryResult:
        return self._disabled("search")

    def shortest_path(self, query: str, *, depth: int = 3, mode: str = "bfs") -> GraphQueryResult:
        return self._disabled("shortest_path")

    def get_neighbors(self, target: str, *, relation: str = "callees_of") -> GraphQueryResult:
        return self._disabled("get_neighbors")

    def get_component(self, name: str) -> GraphQueryResult:
        return self._disabled("get_component")

    def get_file(self, file_path: str) -> GraphQueryResult:
        return self._disabled("get_file")

    def get_route(self, changed_files: list[str] | None = None, *, max_depth: int = 2) -> GraphQueryResult:
        return self._disabled("get_route")

    def query(self, query_type: str, **kwargs: Any) -> GraphQueryResult:
        return self._disabled(query_type)
