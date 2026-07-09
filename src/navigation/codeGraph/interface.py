from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GraphQueryResult:
    ok: bool
    source: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ICodeGraph(ABC):
    @abstractmethod
    def initialize(self) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def refresh(self) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def rebuild(self) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, *, kind: str | None = None, limit: int = 20) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def shortest_path(self, query: str, *, depth: int = 3, mode: str = "bfs") -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def get_neighbors(self, target: str, *, relation: str = "callees_of") -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def get_component(self, name: str) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def get_file(self, file_path: str) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def get_route(self, changed_files: list[str] | None = None, *, max_depth: int = 2) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    def query(self, query_type: str, **kwargs: Any) -> GraphQueryResult:
        raise NotImplementedError

    # Future-facing methods (designed now, can remain no-op in implementations)
    def find_navigation_hint(self, goal: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_navigation_hint", goal=goal, **kwargs)

    def find_relevant_components(self, intent: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_relevant_components", intent=intent, **kwargs)

    def find_likely_route(self, intent: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_likely_route", intent=intent, **kwargs)

    def find_related_files(self, symbol: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_related_files", symbol=symbol, **kwargs)

    def find_button_candidates(self, label_hint: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_button_candidates", label_hint=label_hint, **kwargs)

    def find_component_hierarchy(self, component: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_component_hierarchy", component=component, **kwargs)

    def find_entry_point(self, feature: str, **kwargs: Any) -> GraphQueryResult:
        return self.query("find_entry_point", feature=feature, **kwargs)
