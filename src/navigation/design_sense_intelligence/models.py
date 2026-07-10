"""Design Sense Intelligence — review and critique data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewScope(str, Enum):
	COMPONENT = 'component'
	FEATURE = 'feature'
	FLOW = 'flow'
	PAGE = 'page'
	REGION = 'region'


class ReviewLane(str, Enum):
	"""Objective (deterministic) vs subjective (interpretive) review paths."""

	OBJECTIVE = 'objective'
	SUBJECTIVE = 'subjective'


class FindingSeverity(str, Enum):
	BLOCKING = 'blocking'
	MAJOR = 'major'
	MINOR = 'minor'
	ADVISORY = 'advisory'


class QualityPillar(str, Enum):
	FRICTIONLESS = 'frictionless_insight_to_action'
	CRAFT = 'quality_craft'
	TRUSTWORTHY = 'trustworthy_building'


@dataclass(slots=True)
class ReviewRegion:
	"""UICrit-style region of interest (selector or bounding box)."""

	selector: str | None = None
	x: int | None = None
	y: int | None = None
	width: int | None = None
	height: int | None = None
	label: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'selector': self.selector,
			'x': self.x,
			'y': self.y,
			'width': self.width,
			'height': self.height,
			'label': self.label,
		}


@dataclass(slots=True)
class ReviewFinding:
	"""Single design issue or recommendation."""

	id: str
	category: str
	severity: str
	message: str
	rationale: str = ''
	recommendation: str = ''
	source: str = ''
	pillar: str | None = None
	selector: str | None = None
	region: ReviewRegion | None = None
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'category': self.category,
			'severity': self.severity,
			'message': self.message,
			'rationale': self.rationale,
			'recommendation': self.recommendation,
			'source': self.source,
			'pillar': self.pillar,
			'selector': self.selector,
			'region': self.region.to_dict() if self.region else None,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class DimensionScore:
	"""UICrit-style rubric dimension score."""

	dimension: str
	score: float
	scale: str  # likert_5 | scale_10
	notes: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'dimension': self.dimension,
			'score': self.score,
			'scale': self.scale,
			'notes': self.notes,
		}


@dataclass(slots=True)
class ProviderContribution:
	"""Output from an external or methodology provider."""

	provider: str
	findings: list[ReviewFinding] = field(default_factory=list)
	scores: list[DimensionScore] = field(default_factory=list)
	notes: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'provider': self.provider,
			'findings': [f.to_dict() for f in self.findings],
			'scores': [s.to_dict() for s in self.scores],
			'notes': list(self.notes),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class ReviewRequest:
	"""Inputs for a design review — future fields reserved for browser/DOM/token data."""

	repo_root: str = ''
	preview_url: str | None = None
	scope: str = ReviewScope.PAGE.value
	user_task: str = ''
	region: ReviewRegion | None = None
	dom_snapshot: dict[str, Any] | None = None
	computed_styles: list[dict[str, Any]] | None = None
	html_excerpt: str | None = None
	css_excerpt: str | None = None
	screenshot_ref: str | None = None
	framework: str | None = None
	component_metadata: dict[str, Any] | None = None
	design_tokens: dict[str, Any] | None = None
	open_design_project: str | None = None
	scan_id: str | None = None
	visual_insights: dict[str, Any] | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'repo_root': self.repo_root,
			'preview_url': self.preview_url,
			'scope': self.scope,
			'user_task': self.user_task,
			'region': self.region.to_dict() if self.region else None,
			'has_dom_snapshot': bool(self.dom_snapshot),
			'has_computed_styles': bool(self.computed_styles),
			'screenshot_ref': self.screenshot_ref,
			'framework': self.framework,
			'open_design_project': self.open_design_project,
			'scan_id': self.scan_id,
		}


@dataclass(slots=True)
class ReasoningResult:
	"""Synthesized narrative from objective + subjective signals."""

	narrative: str
	themes: list[str] = field(default_factory=list)
	strengths: list[str] = field(default_factory=list)
	concerns: list[str] = field(default_factory=list)
	recommendations: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'narrative': self.narrative,
			'themes': list(self.themes),
			'strengths': list(self.strengths),
			'concerns': list(self.concerns),
			'recommendations': list(self.recommendations),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class LaneReviewBundle:
	"""Findings and scores from one review lane before merge."""

	lane: str
	findings: list[ReviewFinding] = field(default_factory=list)
	scores: list[DimensionScore] = field(default_factory=list)
	notes: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DesignReviewReport:
	"""Merged output from coordinator, specialists, providers, and reasoning."""

	passed: bool
	summary: str
	findings: list[ReviewFinding] = field(default_factory=list)
	objective_findings: list[ReviewFinding] = field(default_factory=list)
	subjective_findings: list[ReviewFinding] = field(default_factory=list)
	scores: list[DimensionScore] = field(default_factory=list)
	pillars: dict[str, list[str]] = field(default_factory=dict)
	reasoning: ReasoningResult | None = None
	consulted_providers: list[str] = field(default_factory=list)
	consulted_reviewers: list[str] = field(default_factory=list)
	workflow_phases: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'passed': self.passed,
			'summary': self.summary,
			'findings': [f.to_dict() for f in self.findings],
			'objective_findings': [f.to_dict() for f in self.objective_findings],
			'subjective_findings': [f.to_dict() for f in self.subjective_findings],
			'scores': [s.to_dict() for s in self.scores],
			'pillars': {k: list(v) for k, v in self.pillars.items()},
			'reasoning': self.reasoning.to_dict() if self.reasoning else None,
			'consulted_providers': list(self.consulted_providers),
			'consulted_reviewers': list(self.consulted_reviewers),
			'workflow_phases': list(self.workflow_phases),
			'degraded': list(self.degraded),
		}
