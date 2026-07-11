"""Shared knowledge types — sourced from Gemini research (structured, not loaded at runtime)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class KnowledgeTopic:
	id: str
	section: str
	title: str
	category: str
	reviewer: str
	lane: str
	definition: str
	key_rules: tuple[str, ...] = ()
	common_mistakes: tuple[str, ...] = ()
	evaluation_criteria: str = ''
	terminology: tuple[str, ...] = ()
	keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HeuristicEntry:
	id: str
	title: str
	description: str
	evaluation_prompt: str


@dataclass(frozen=True, slots=True)
class PsychologyLaw:
	id: str
	title: str
	formula: str
	design_implication: str


@dataclass(frozen=True, slots=True)
class EvaluationChecklist:
	domain: str
	reviewer: str
	lane: str
	items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SeverityLevel:
	level: int
	designation: str
	interpretation: str
