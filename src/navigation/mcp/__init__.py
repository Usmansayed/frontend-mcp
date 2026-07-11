"""Frontend Perception MCP package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from .server import PerceptionMCPServer

__all__ = ['PerceptionMCPServer', 'main']


def __getattr__(name: str):
	if name == 'PerceptionMCPServer':
		from .server import PerceptionMCPServer

		return PerceptionMCPServer
	if name == 'main':
		from .server import main

		return main
	raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
