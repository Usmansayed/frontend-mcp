"""Resolve UX KB corpus paths: local ForOpenCode override, else packaged data."""
from __future__ import annotations

from pathlib import Path


def packaged_data_root() -> Path:
	return Path(__file__).resolve().parent / "data"


def corpus_usable(graphs_dir: Path, runtime_dir: Path) -> bool:
	nodes = graphs_dir / "nodes.json"
	edges = graphs_dir / "edges.json"
	if not nodes.is_file() or not edges.is_file():
		return False
	if not runtime_dir.is_dir():
		return False
	return any(runtime_dir.glob("pack_*.json"))


def resolve_ux_kb_paths(repo_root: Path | str | None = None) -> tuple[Path, Path, Path, Path, str]:
	"""Return (graphs_dir, runtime_dir, db_path, corpus_root, source).

	source is ``repo`` when ``{repo_root}/ForOpenCode`` has graphs+packs,
	otherwise ``packaged`` bundled under ``navigation.ux_knowledge.data``.
	"""
	pkg = packaged_data_root()
	pkg_graphs = pkg / "08_graphs"
	pkg_runtime = pkg / "09_runtime"
	pkg_db = pkg / "ux_kb.sqlite"  # optional; cards.json is preferred fallback

	if repo_root:
		root = Path(repo_root).resolve()
		foropencode = root / "ForOpenCode"
		graphs = foropencode / "08_graphs"
		runtime = foropencode / "09_runtime"
		db = foropencode / "kb" / "ux_kb.sqlite"
		if corpus_usable(graphs, runtime):
			return graphs, runtime, db, foropencode, "repo"

	if corpus_usable(pkg_graphs, pkg_runtime):
		return pkg_graphs, pkg_runtime, pkg_db, pkg, "packaged"

	# Last resort: cwd ForOpenCode (dev convenience)
	cwd_fo = Path.cwd().resolve() / "ForOpenCode"
	return (
		cwd_fo / "08_graphs",
		cwd_fo / "09_runtime",
		cwd_fo / "kb" / "ux_kb.sqlite",
		cwd_fo,
		"cwd",
	)
