"""Load project `.env` for local dev (credentials stay out of git)."""
from __future__ import annotations

import os
from pathlib import Path


def find_project_root(start: Path | None = None) -> Path | None:
	"""Walk upward until pyproject.toml or .git is found."""
	current = (start or Path.cwd()).resolve()
	for directory in (current, *current.parents):
		if (directory / 'pyproject.toml').is_file() or (directory / '.git').exists():
			return directory
	return None


def load_project_env(*, override: bool = False) -> Path | None:
	"""
	Load `.env` from repo root into os.environ.

	Override path with FRONTEND_PERCEPTION_ENV_FILE. Returns loaded path or None.
	"""
	explicit = os.environ.get('FRONTEND_PERCEPTION_ENV_FILE', '').strip()
	if explicit:
		path = Path(explicit).expanduser().resolve()
		if path.is_file():
			_load_file(path, override=override)
			return path
		return None

	root = find_project_root()
	if root is None:
		return None
	path = root / '.env'
	if path.is_file():
		_load_file(path, override=override)
		return path
	return None


def _load_file(path: Path, *, override: bool) -> None:
	try:
		from dotenv import load_dotenv
	except ImportError:
		return
	load_dotenv(path, override=override)
