"""Compatibility module for ``import frontend_mcp``.

Version always mirrors the installed ``frontend-mcp`` distribution
(legacy ``frontend-perception-engine`` name still accepted).
"""
from __future__ import annotations

try:
	from navigation.core.package_meta import installed_version

	__version__ = installed_version(default="0.0.0")
except Exception:  # pragma: no cover
	__version__ = "0.0.0"

__all__ = ["__version__"]
