"""Observation snapshots keyed by scan_id (for diff and audit)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScanRecord:
    scan_id: str
    session_id: str
    run_id: str
    url: str
    observation: dict[str, Any]
    screenshot_path: str | None = None


class ScanRegistry:
    def __init__(self) -> None:
        self._scans: dict[str, ScanRecord] = {}

    def register(
        self,
        *,
        session_id: str,
        run_id: str,
        url: str,
        observation: dict[str, Any],
    ) -> ScanRecord:
        scan_id = f"scan_{uuid.uuid4().hex[:12]}"
        rec = ScanRecord(
            scan_id=scan_id,
            session_id=session_id,
            run_id=run_id,
            url=url,
            observation=observation,
            screenshot_path=observation.get("screenshot_path"),
        )
        self._scans[scan_id] = rec
        return rec

    def get(self, scan_id: str) -> ScanRecord | None:
        return self._scans.get(scan_id)

    def all(self) -> list[ScanRecord]:
        return list(self._scans.values())
