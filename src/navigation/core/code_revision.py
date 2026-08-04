"""In-memory code revision — must match pyproject package version after each ship.

Health compares this to importlib package metadata. When an agent installs a new
wheel without restarting the MCP process, package_version updates (disk) while
CODE_REVISION stays on the old loaded module → version_skew=true.

Prefer reading VERSION / package metadata so ship bumps stay in lockstep.
"""

from __future__ import annotations

from navigation.core.package_meta import installed_version

# Resolved once at import — restart MCP after version bumps so this refreshes.
CODE_REVISION = installed_version(default="0.0.0+unknown")
