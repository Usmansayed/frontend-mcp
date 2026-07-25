"""In-memory code revision — must match pyproject package version after each ship.

Health compares this to importlib package metadata. When an agent installs a new
wheel without restarting the MCP process, package_version updates (disk) while
CODE_REVISION stays on the old loaded module → version_skew=true.
"""

from __future__ import annotations

# Bump in lockstep with pyproject.toml [project].version on every publish.
CODE_REVISION = "1.2.0.dev46"
