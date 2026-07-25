"""Compatibility module — same package as frontend-perception-engine.

Historically ``frontend-mcp`` was a separate PyPI alias that caused version skew.
Version always comes from the single installed engine package.
"""
from __future__ import annotations

try:
	from importlib.metadata import PackageNotFoundError, version
except ImportError:  # pragma: no cover
	from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
	__version__ = version('frontend-perception-engine')
except PackageNotFoundError:  # pragma: no cover
	__version__ = '0.0.0'

__all__ = ['__version__']
