"""Register all Knowledge API query handlers."""
from __future__ import annotations

from .components import COMPONENT_HANDLERS
from .consistency import CONSISTENCY_HANDLERS
from .foundations import FOUNDATION_HANDLERS
from .graph_queries import GRAPH_HANDLERS
from .tokens import TOKEN_HANDLERS

ALL_HANDLERS: dict[str, object] = {}
for group in (FOUNDATION_HANDLERS, COMPONENT_HANDLERS, TOKEN_HANDLERS, CONSISTENCY_HANDLERS, GRAPH_HANDLERS):
	ALL_HANDLERS.update(group)
