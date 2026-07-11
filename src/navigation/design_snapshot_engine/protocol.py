"""Extractor protocol — each module observes, never critiques."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .models import DesignSnapshot
from .raw_context import RawBrowserContext


@runtime_checkable
class DesignExtractor(Protocol):
	"""Independent extractor: raw browser context → one snapshot section."""

	name: str

	def extract(self, context: RawBrowserContext) -> dict[str, Any]:
		"""Return partial snapshot dict keyed by section name (e.g. typography)."""
		...


def merge_sections(base: DesignSnapshot, sections: list[dict[str, Any]]) -> DesignSnapshot:
	"""Merge extractor outputs into unified snapshot."""
	for section in sections:
		for key, value in section.items():
			if not hasattr(base, key):
				continue
			current = getattr(base, key)
			if hasattr(current, '__dataclass_fields__'):
				for field_name, field_val in (value or {}).items():
					if hasattr(current, field_name):
						setattr(current, field_name, field_val)
	return base
