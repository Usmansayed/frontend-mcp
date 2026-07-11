"""Reference registry models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReferenceEntry:
	"""A named reference product with extracted design snapshot."""

	id: str
	name: str
	tags: list[str] = field(default_factory=list)
	snapshot: dict[str, Any] = field(default_factory=dict)
	source_url: str = ''
	notes: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'name': self.name,
			'tags': list(self.tags),
			'snapshot': dict(self.snapshot),
			'source_url': self.source_url,
			'notes': self.notes,
		}


@dataclass(slots=True)
class SnapshotComparison:
	"""Structural comparison between current and reference snapshots."""

	reference_id: str
	reference_name: str
	similarity_score: float
	dimension_scores: dict[str, float] = field(default_factory=dict)
	recommendations: list[str] = field(default_factory=list)
	gaps: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'reference_id': self.reference_id,
			'reference_name': self.reference_name,
			'similarity_score': self.similarity_score,
			'dimension_scores': dict(self.dimension_scores),
			'recommendations': list(self.recommendations),
			'gaps': list(self.gaps),
		}
