"""Figma session — active file, page, frame, selection."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FigmaSessionState:
	file_key: str = ''
	file_url: str = ''
	file_name: str = ''
	active_page_id: str = ''
	active_frame_id: str = ''
	selection_node_ids: list[str] = field(default_factory=list)
	known_files: list[dict[str, str]] = field(default_factory=list)
	updated_at: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'file_key': self.file_key,
			'file_url': self.file_url,
			'file_name': self.file_name,
			'active_page_id': self.active_page_id,
			'active_frame_id': self.active_frame_id,
			'selection_node_ids': list(self.selection_node_ids),
			'known_files': list(self.known_files),
			'updated_at': self.updated_at,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> FigmaSessionState:
		return cls(
			file_key=str(data.get('file_key') or ''),
			file_url=str(data.get('file_url') or ''),
			file_name=str(data.get('file_name') or ''),
			active_page_id=str(data.get('active_page_id') or ''),
			active_frame_id=str(data.get('active_frame_id') or ''),
			selection_node_ids=[str(x) for x in (data.get('selection_node_ids') or []) if x],
			known_files=list(data.get('known_files') or []),
			updated_at=float(data.get('updated_at') or 0.0),
		)


def session_path() -> Path:
	raw = os.environ.get('FIGMA_SESSION_PATH', '').strip()
	if raw:
		return Path(raw)
	cache = os.environ.get('FIGMA_CACHE_DIR', '.cache').strip() or '.cache'
	return Path(cache) / 'figma_session.json'


class FigmaSessionManager:
	def __init__(self, *, path: Path | None = None) -> None:
		self._path = path or session_path()
		self._state: FigmaSessionState | None = None

	def load(self) -> FigmaSessionState:
		if self._state is not None:
			return self._state
		if self._path.is_file():
			try:
				raw = json.loads(self._path.read_text(encoding='utf-8'))
				if isinstance(raw, dict):
					self._state = FigmaSessionState.from_dict(raw)
					return self._state
			except json.JSONDecodeError:
				pass
		self._state = FigmaSessionState()
		return self._state

	def save(self, state: FigmaSessionState | None = None) -> None:
		state = state or self.load()
		state.updated_at = time.time()
		self._state = state
		self._path.parent.mkdir(parents=True, exist_ok=True)
		self._path.write_text(json.dumps(state.to_dict(), indent=2), encoding='utf-8')

	def set_active_file(
		self,
		*,
		file_key: str = '',
		file_url: str = '',
		file_name: str = '',
	) -> FigmaSessionState:
		state = self.load()
		if file_key:
			state.file_key = file_key
		if file_url:
			state.file_url = file_url
		if file_name:
			state.file_name = file_name
		self._register_known_file(state, file_key=state.file_key, file_url=state.file_url, file_name=state.file_name)
		self.save(state)
		return state

	def set_active_page(self, page_id: str) -> FigmaSessionState:
		state = self.load()
		state.active_page_id = page_id
		self.save(state)
		return state

	def set_active_frame(self, frame_id: str) -> FigmaSessionState:
		state = self.load()
		state.active_frame_id = frame_id
		self.save(state)
		return state

	def set_selection(self, node_ids: list[str]) -> FigmaSessionState:
		state = self.load()
		state.selection_node_ids = [nid for nid in node_ids if nid]
		self.save(state)
		return state

	def _register_known_file(
		self,
		state: FigmaSessionState,
		*,
		file_key: str,
		file_url: str,
		file_name: str,
	) -> None:
		if not file_key and not file_url:
			return
		entry = {'file_key': file_key, 'file_url': file_url, 'file_name': file_name}
		existing = [f for f in state.known_files if f.get('file_key') != file_key]
		existing.insert(0, entry)
		state.known_files = existing[:20]
