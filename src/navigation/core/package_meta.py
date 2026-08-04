"""Installed distribution name/version for Frontend MCP.

Primary PyPI name is ``frontend-mcp``. ``frontend-perception-engine`` remains a
thin reverse alias for old install commands.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

# Prefer the user-facing name; fall back to the legacy engine name.
DIST_CANDIDATES: tuple[str, ...] = ("frontend-mcp", "frontend-perception-engine")


def installed_dist_name() -> str | None:
	for name in DIST_CANDIDATES:
		try:
			metadata.version(name)
			return name
		except metadata.PackageNotFoundError:
			continue
	return None


def installed_version(*, default: str = "0.0.0") -> str:
	# Prefer repo VERSION when running from a source checkout (PYTHONPATH=src).
	version_path = Path(__file__).resolve().parents[3] / "VERSION"
	try:
		text = version_path.read_text(encoding="utf-8").strip()
		if text:
			return text
	except OSError:
		pass
	for name in DIST_CANDIDATES:
		try:
			return metadata.version(name)
		except metadata.PackageNotFoundError:
			continue
	return default


def distribution_for_mtime():
	"""Return importlib.metadata.Distribution for the installed primary package."""
	for name in DIST_CANDIDATES:
		try:
			return metadata.distribution(name)
		except metadata.PackageNotFoundError:
			continue
	return None
