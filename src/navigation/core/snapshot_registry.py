"""Design snapshot storage keyed by snapshot_id (linked to scan_id)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class SnapshotRecord:
	snapshot_id: str
	scan_id: str | None
	session_id: str | None
	url: str
	snapshot: dict[str, Any]

	def to_dict(self) -> dict[str, Any]:
		return {
			'snapshot_id': self.snapshot_id,
			'scan_id': self.scan_id,
			'session_id': self.session_id,
			'url': self.url,
			'snapshot': self.snapshot,
		}


class SnapshotRegistry:
	def __init__(self) -> None:
		self._snapshots: dict[str, SnapshotRecord] = {}

	def register(
		self,
		*,
		snapshot: dict[str, Any],
		url: str,
		scan_id: str | None = None,
		session_id: str | None = None,
		snapshot_id: str | None = None,
	) -> SnapshotRecord:
		sid = snapshot_id or f"snap_{uuid.uuid4().hex[:12]}"
		rec = SnapshotRecord(
			snapshot_id=sid,
			scan_id=scan_id,
			session_id=session_id,
			url=url,
			snapshot=snapshot,
		)
		self._snapshots[sid] = rec
		return rec

	def get(self, snapshot_id: str) -> SnapshotRecord | None:
		return self._snapshots.get(snapshot_id)

	def get_by_scan(self, scan_id: str) -> SnapshotRecord | None:
		for rec in self._snapshots.values():
			if rec.scan_id == scan_id:
				return rec
		return None

	def all(self) -> list[SnapshotRecord]:
		return list(self._snapshots.values())
