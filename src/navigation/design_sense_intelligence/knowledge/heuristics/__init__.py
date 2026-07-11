"""Nielsen heuristics and Gestalt principles — from epistemology research."""
from __future__ import annotations

from ..epistemology import GESTALT_PRINCIPLES, NIELSEN_HEURISTICS
from ..types import HeuristicEntry

__all__ = ['GESTALT_PRINCIPLES', 'NIELSEN_HEURISTICS', 'HeuristicEntry', 'all_heuristics']


def all_heuristics() -> list[HeuristicEntry]:
	return list(NIELSEN_HEURISTICS) + list(GESTALT_PRINCIPLES)
