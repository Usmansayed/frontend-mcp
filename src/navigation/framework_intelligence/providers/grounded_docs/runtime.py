"""Cross-platform runtime helpers for Grounded Docs CLI invocation."""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

MIN_NODE_MAJOR = 22


def augment_path_for_node() -> None:
	"""Ensure common Node install dirs are on PATH (IDE-launched MCP often lacks them)."""
	extra: list[str] = []
	if sys.platform == 'win32':
		for key in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
			raw = os.environ.get(key, '').strip()
			if not raw:
				continue
			base = Path(raw)
			for sub in ('nodejs', Path('Programs') / 'node'):
				candidate = base / sub
				if candidate.is_dir():
					extra.append(str(candidate))
	else:
		for candidate in (
			Path('/usr/local/bin'),
			Path('/opt/homebrew/bin'),
			Path.home() / '.nvm' / 'versions' / 'node',
		):
			if candidate.is_dir():
				extra.append(str(candidate))
	if not extra:
		return
	current = os.environ.get('PATH', '')
	parts = current.split(os.pathsep) if current else []
	for entry in extra:
		if entry not in parts:
			parts.insert(0, entry)
	os.environ['PATH'] = os.pathsep.join(parts)


def resolve_executable(name: str) -> str | None:
	augment_path_for_node()
	return shutil.which(name)


def parse_node_major_version(version_text: str) -> int | None:
	match = re.search(r'v?(\d+)', version_text.strip())
	if not match:
		return None
	return int(match.group(1))


def default_store_path(repo_root: str | None) -> Path:
	env_raw = os.environ.get('GROUNDED_DOCS_STORE_PATH', '').strip()
	if env_raw:
		return Path(env_raw).expanduser().resolve()
	if repo_root:
		return (Path(repo_root).expanduser().resolve() / 'artifacts' / 'grounded-docs-store')
	cache_home = os.environ.get('XDG_CACHE_HOME', '').strip()
	if cache_home:
		return Path(cache_home).expanduser().resolve() / 'frontend-perception' / 'grounded-docs-store'
	return Path.home() / '.cache' / 'frontend-perception' / 'grounded-docs-store'


def ensure_store_dir(store_path: Path) -> Path:
	resolved = store_path.expanduser().resolve()
	resolved.mkdir(parents=True, exist_ok=True)
	return resolved
