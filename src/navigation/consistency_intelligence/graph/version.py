"""Graph versioning utilities."""
from __future__ import annotations

from datetime import datetime, timezone


def new_graph_version() -> str:
	"""Generate a new graph version identifier."""
	ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
	us = datetime.now(timezone.utc).microsecond
	return f'pdg_{ts}.{us:06d}Z'
