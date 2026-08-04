"""Secure local storage for Figma Personal Access Token."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def token_path() -> Path:
	raw = os.environ.get('FIGMA_TOKEN_PATH', '').strip() or os.environ.get(
		'FIGMA_CACHE_DIR', '.cache'
	).strip()
	base = Path(raw)
	if base.suffix == '.json':
		return base
	return base / 'figma_tokens.json'


def load_tokens() -> dict[str, Any]:
	path = token_path()
	if not path.is_file():
		return {}
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
	except json.JSONDecodeError:
		return {}
	return data if isinstance(data, dict) else {}


def save_pat(pat: str, *, account_hint: str = '') -> None:
	path = token_path()
	path.parent.mkdir(parents=True, exist_ok=True)
	payload = {
		'version': 1,
		'pat': pat.strip(),
		'account_hint': account_hint,
		'connected_at': time.time(),
	}
	path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def get_pat() -> str:
	data = load_tokens()
	pat = str(data.get('pat') or '').strip()
	if pat:
		return pat
	return (
		os.environ.get('FIGMA_ACCESS_TOKEN', '').strip()
		or os.environ.get('FIGMA_PAT', '').strip()
		or os.environ.get('figma_pat', '').strip()
	)


def has_stored_pat() -> bool:
	return bool(get_pat())


def clear_pat() -> None:
	path = token_path()
	if path.is_file():
		path.unlink(missing_ok=True)
