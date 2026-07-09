from __future__ import annotations

from pathlib import Path

from .crg_impl import CRGCodeGraph
from .interface import ICodeGraph
from .null_impl import NullCodeGraph


def create_code_graph(repo_root: str | Path, enabled: bool = True) -> ICodeGraph:
    if not enabled:
        return NullCodeGraph()
    graph = CRGCodeGraph(repo_root=repo_root)
    init = graph.initialize()
    if not init.ok:
        return NullCodeGraph()
    # First-time sandbox: incremental init may succeed with 0 nodes — force full build.
    stats = graph.query("stats")
    node_count = (stats.payload or {}).get("node_count", 0)
    if node_count == 0:
        rebuild = graph.rebuild()
        if not rebuild.ok:
            return NullCodeGraph()
    return graph
