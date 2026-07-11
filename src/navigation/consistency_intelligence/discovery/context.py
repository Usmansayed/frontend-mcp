"""Discovery context passed to all knowledge sources."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DiscoveryContext:
	"""Inputs available to knowledge sources during a pipeline run."""

	project_id: str = 'default'
	repo_root: Path | None = None
	design_snapshot: Any | None = None  # DesignSnapshot
	scan_id: str | None = None
	enabled_sources: frozenset[str] = frozenset({'snapshot', 'codebase', 'tokens'})
	options: dict[str, Any] = field(default_factory=dict)
