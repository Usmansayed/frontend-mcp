"""Tiny disk persistence for inspiration process caches (affinity/SERP/result/cooldown)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def cache_dir() -> Path:
	root = Path(os.environ.get('INSPIRATION_CACHE_DIR', '.cache'))
	root.mkdir(parents=True, exist_ok=True)
	return root


def cache_path(name: str) -> Path:
	return cache_dir() / name


def load_json_dict(path: Path) -> dict[str, Any]:
	if not path.exists():
		return {}
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
		return data if isinstance(data, dict) else {}
	except (json.JSONDecodeError, OSError):
		return {}


def save_json_dict(path: Path, data: dict[str, Any]) -> None:
	try:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding='utf-8')
	except OSError:
		pass
