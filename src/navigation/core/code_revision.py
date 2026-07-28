"""In-memory code revision — must match pyproject package version after each ship.

Health compares this to importlib package metadata. When an agent installs a new
wheel without restarting the MCP process, package_version updates (disk) while
CODE_REVISION stays on the old loaded module → version_skew=true.

Prefer reading VERSION / package metadata so ship bumps stay in lockstep.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

_PKG = "frontend-perception-engine"


def _read_revision() -> str:
	# Prefer repo VERSION when running from a source checkout (PYTHONPATH=src).
	# Installed dist-info often lags behind ship bumps until `pip install -e .`.
	version_path = Path(__file__).resolve().parents[3] / "VERSION"
	try:
		text = version_path.read_text(encoding="utf-8").strip()
		if text:
			return text
	except OSError:
		pass
	try:
		return metadata.version(_PKG)
	except Exception:
		pass
	return "0.0.0+unknown"


# Resolved once at import — restart MCP after version bumps so this refreshes.
CODE_REVISION = _read_revision()
