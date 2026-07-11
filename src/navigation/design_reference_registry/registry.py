"""In-memory design reference registry (file-backed persistence optional)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot

from .comparison import find_similar_references
from .models import ReferenceEntry, SnapshotComparison


class DesignReferenceRegistry:
	"""Store extracted DesignSnapshots as structural references."""

	def __init__(self, *, storage_path: Path | None = None) -> None:
		self._entries: dict[str, ReferenceEntry] = {}
		self._storage_path = storage_path

	def register(
		self,
		entry_id: str,
		name: str,
		snapshot: DesignSnapshot,
		*,
		tags: list[str] | None = None,
		source_url: str = '',
		notes: str = '',
	) -> ReferenceEntry:
		entry = ReferenceEntry(
			id=entry_id,
			name=name,
			tags=list(tags or []),
			snapshot=snapshot.to_dict(),
			source_url=source_url,
			notes=notes,
		)
		self._entries[entry_id] = entry
		if self._storage_path:
			self._persist()
		return entry

	def get(self, entry_id: str) -> ReferenceEntry | None:
		return self._entries.get(entry_id)

	def list_entries(self) -> list[ReferenceEntry]:
		return list(self._entries.values())

	def find_similar(
		self,
		snapshot: DesignSnapshot,
		*,
		limit: int = 5,
		user_task: str = '',
	) -> list[SnapshotComparison]:
		return find_similar_references(
			snapshot,
			self.list_entries(),
			limit=limit,
			user_task=user_task,
		)

	def compare(self, current: DesignSnapshot, reference_id: str) -> SnapshotComparison | None:
		entry = self.get(reference_id)
		if entry is None:
			return None
		from .comparison import compare_snapshots

		return compare_snapshots(
			current,
			DesignSnapshot.from_dict(entry.snapshot),
			reference_id=entry.id,
			reference_name=entry.name,
		)

	def load(self, path: Path | None = None) -> None:
		p = path or self._storage_path
		if p is None or not p.exists():
			return
		data = json.loads(p.read_text(encoding='utf-8'))
		for item in data.get('entries') or []:
			entry = ReferenceEntry(**item)
			self._entries[entry.id] = entry

	def _persist(self) -> None:
		if self._storage_path is None:
			return
		self._storage_path.parent.mkdir(parents=True, exist_ok=True)
		payload: dict[str, Any] = {
			'entries': [e.to_dict() for e in self._entries.values()],
		}
		self._storage_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
