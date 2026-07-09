from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .interface import GraphQueryResult, ICodeGraph

CRGError = Exception
_build_or_update_graph: Callable[..., dict[str, Any]] | None = None
_query_graph: Callable[..., dict[str, Any]] | None = None
_semantic_search_nodes: Callable[..., dict[str, Any]] | None = None
_get_impact_radius: Callable[..., dict[str, Any]] | None = None
_list_graph_stats: Callable[..., dict[str, Any]] | None = None
_traverse_graph_func: Callable[..., dict[str, Any]] | None = None

try:
    from code_review_graph.tools.build import build_or_update_graph as _build_or_update_graph
    from code_review_graph.tools.query import (
        get_impact_radius as _get_impact_radius,
        list_graph_stats as _list_graph_stats,
        query_graph as _query_graph,
        semantic_search_nodes as _semantic_search_nodes,
        traverse_graph_func as _traverse_graph_func,
    )
except Exception as exc:  # pragma: no cover - defensive import
    CRGError = type(exc)


class CRGCodeGraph(ICodeGraph):
    """CRG-backed code graph adapter hidden behind ICodeGraph."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = str(Path(repo_root))

    def _ok(self, summary: str, payload: dict[str, Any]) -> GraphQueryResult:
        return GraphQueryResult(ok=True, source="crg", summary=summary, payload=payload)

    def _err(self, action: str, exc: Exception) -> GraphQueryResult:
        return GraphQueryResult(
            ok=False,
            source="crg",
            summary=f"CRG {action} failed.",
            error=str(exc),
        )

    @staticmethod
    def _ensure_available() -> None:
        required = [
            _build_or_update_graph,
            _query_graph,
            _semantic_search_nodes,
            _get_impact_radius,
            _list_graph_stats,
            _traverse_graph_func,
        ]
        if any(fn is None for fn in required):
            raise RuntimeError("code-review-graph is not available")

    def initialize(self) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _build_or_update_graph(repo_root=self.repo_root, full_rebuild=False, postprocess="minimal")
            return self._ok(payload.get("summary", "Graph initialized"), payload)
        except Exception as exc:
            return self._err("initialize", exc)

    def refresh(self) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _build_or_update_graph(repo_root=self.repo_root, full_rebuild=False)
            return self._ok(payload.get("summary", "Graph refreshed"), payload)
        except Exception as exc:
            return self._err("refresh", exc)

    def rebuild(self) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _build_or_update_graph(repo_root=self.repo_root, full_rebuild=True)
            return self._ok(payload.get("summary", "Graph rebuilt"), payload)
        except Exception as exc:
            return self._err("rebuild", exc)

    def search(self, query: str, *, kind: str | None = None, limit: int = 20) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _semantic_search_nodes(query=query, kind=kind, limit=limit, repo_root=self.repo_root)
            return self._ok(payload.get("summary", f"Search for {query}"), payload)
        except Exception as exc:
            return self._err("search", exc)

    def shortest_path(self, query: str, *, depth: int = 3, mode: str = "bfs") -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _traverse_graph_func(query=query, depth=depth, mode=mode, repo_root=self.repo_root)
            return self._ok(payload.get("summary", f"Traversal for {query}"), payload)
        except Exception as exc:
            return self._err("shortest_path", exc)

    def get_neighbors(self, target: str, *, relation: str = "callees_of") -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _query_graph(pattern=relation, target=target, repo_root=self.repo_root)
            return self._ok(payload.get("summary", f"{relation} for {target}"), payload)
        except Exception as exc:
            return self._err("get_neighbors", exc)

    def get_component(self, name: str) -> GraphQueryResult:
        return self.search(name, kind="Class", limit=10)

    def get_file(self, file_path: str) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _query_graph(pattern="file_summary", target=file_path, repo_root=self.repo_root)
            return self._ok(payload.get("summary", f"File summary for {file_path}"), payload)
        except Exception as exc:
            return self._err("get_file", exc)

    def get_route(self, changed_files: list[str] | None = None, *, max_depth: int = 2) -> GraphQueryResult:
        try:
            self._ensure_available()
            payload = _get_impact_radius(
                changed_files=changed_files,
                max_depth=max_depth,
                repo_root=self.repo_root,
            )
            return self._ok(payload.get("summary", "Impact route"), payload)
        except Exception as exc:
            return self._err("get_route", exc)

    def query(self, query_type: str, **kwargs: Any) -> GraphQueryResult:
        # Public, graph-agnostic API contract for current + future methods.
        if query_type == "search":
            return self.search(kwargs["query"], kind=kwargs.get("kind"), limit=kwargs.get("limit", 20))
        if query_type == "neighbors":
            return self.get_neighbors(kwargs["target"], relation=kwargs.get("relation", "callees_of"))
        if query_type == "component":
            return self.get_component(kwargs["name"])
        if query_type == "file":
            return self.get_file(kwargs["file_path"])
        if query_type == "route":
            return self.get_route(kwargs.get("changed_files"), max_depth=kwargs.get("max_depth", 2))
        if query_type == "shortest_path":
            return self.shortest_path(kwargs["query"], depth=kwargs.get("depth", 3), mode=kwargs.get("mode", "bfs"))
        if query_type == "stats":
            try:
                self._ensure_available()
                payload = _list_graph_stats(repo_root=self.repo_root)
                return self._ok(payload.get("summary", "Graph stats"), payload)
            except Exception as exc:
                return self._err("stats", exc)

        # Future API shape examples (defer to search/traversal today):
        if query_type in {
            "find_navigation_hint",
            "find_relevant_components",
            "find_likely_route",
            "find_related_files",
            "find_button_candidates",
            "find_component_hierarchy",
            "find_entry_point",
        }:
            prompt = " ".join(str(v) for v in kwargs.values())
            return self.search(prompt, limit=10)

        return GraphQueryResult(
            ok=False,
            source="crg",
            summary=f"Unknown query type: {query_type}",
            error="unknown_query_type",
        )
