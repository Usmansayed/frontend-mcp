"""CLI package entry: python -m foropencode_pipeline (with PYTHONPATH=scripts)."""
from __future__ import annotations

import runpy
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
	# Delegate to runner which lives next to this package's parent
	runner = Path(__file__).resolve().parents[1] / "run_foropencode_pipeline.py"
	# Import runner main
	import importlib.util

	spec = importlib.util.spec_from_file_location("run_foropencode_pipeline", runner)
	mod = importlib.util.module_from_spec(spec)
	assert spec.loader
	spec.loader.exec_module(mod)
	return mod.main(argv)
