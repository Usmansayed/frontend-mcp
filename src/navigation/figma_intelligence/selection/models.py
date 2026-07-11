"""Selection Planner — budget-aware retrieval after ranking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.figma_intelligence.models import FigmaRankedCandidate


@dataclass(slots=True)
class SelectionBudget:
	"""API/rate-limit aware extraction budget."""

	initial_open: int = 3
	fallback_open: int = 5
	max_total_open: int = 8
	confidence_stop_threshold: float = 0.85
	max_api_calls: int = 12

	def to_dict(self) -> dict[str, Any]:
		return {
			'initial_open': self.initial_open,
			'fallback_open': self.fallback_open,
			'max_total_open': self.max_total_open,
			'confidence_stop_threshold': self.confidence_stop_threshold,
			'max_api_calls': self.max_api_calls,
		}


@dataclass(slots=True)
class SelectedCandidate:
	"""One candidate approved for provider extraction."""

	ranked: FigmaRankedCandidate
	batch_number: int
	open_reason: str
	design_system_key: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'ranked': self.ranked.to_dict(),
			'batch_number': self.batch_number,
			'open_reason': self.open_reason,
			'design_system_key': self.design_system_key,
		}


@dataclass(slots=True)
class SelectionPlan:
	"""Who is worth opening — distinct from ranking (who is best)."""

	selected: list[SelectedCandidate] = field(default_factory=list)
	reserve: list[FigmaRankedCandidate] = field(default_factory=list)
	budget: SelectionBudget = field(default_factory=SelectionBudget)
	stop_when_confidence_met: bool = True
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'selected': [s.to_dict() for s in self.selected],
			'reserve_count': len(self.reserve),
			'budget': self.budget.to_dict(),
			'stop_when_confidence_met': self.stop_when_confidence_met,
			'degraded': list(self.degraded),
		}

	@property
	def batch_numbers(self) -> list[int]:
		return sorted({s.batch_number for s in self.selected})
