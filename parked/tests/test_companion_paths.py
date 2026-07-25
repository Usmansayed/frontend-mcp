"""Companion path resolution — Windows venv cwd bug regression."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.seo_intelligence.setup.companion_processes import (
	companion_venv,
	companions_cache_dir,
	venv_python_path,
)


def test_venv_python_is_absolute_under_companions_cache() -> None:
	cache = companions_cache_dir().resolve()
	venv = companion_venv().resolve()
	py = venv_python_path(venv)
	assert cache in py.parents or py.parent == cache
	assert py.name in {'python.exe', 'python'}
	assert venv.is_absolute()
