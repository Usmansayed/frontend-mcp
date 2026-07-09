"""Codebase intelligence service facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph import create_code_graph
from .graph.interface import GraphQueryResult, ICodeGraph


class CodebaseIntelligenceService:
	def __init__(self, repo_root: Path, *, enabled: bool = True) -> None:
		self._graph = create_code_graph(repo_root, enabled=enabled)

	def query(self, query_type: str, **kwargs: Any) -> GraphQueryResult:
		return self._graph.query(query_type, **kwargs)

	@property
	def graph(self) -> ICodeGraph:
		return self._graph
