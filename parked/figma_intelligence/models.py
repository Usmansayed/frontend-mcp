"""Figma Intelligence data models — stable contracts for pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FigmaIntentKind(str, Enum):
	"""High-level agent goal when invoking Figma Intelligence."""

	INSPIRE = 'inspire'  # find community templates for reference
	EXTRACT_DS = 'extract_design_system'  # tokens, variables, components
	COMPARE = 'compare'  # diff against project / reference registry
	REUSE_COMPONENT = 'reuse_component'  # find installable component DNA
	LEARN_PATTERNS = 'learn_patterns'  # feed PDG / reference registry


@dataclass(slots=True)
class FigmaIntent:
	"""Parsed agent goal — drives planning and discovery."""

	kind: FigmaIntentKind
	raw_query: str = ''
	target_styles: list[str] = field(default_factory=list)  # e.g. dashboard, saas, mobile
	constraints: dict[str, Any] = field(default_factory=dict)
	project_id: str = 'default'
	repo_root: str = ''

	def to_dict(self) -> dict[str, Any]:
		return {
			'kind': self.kind.value,
			'raw_query': self.raw_query,
			'target_styles': list(self.target_styles),
			'constraints': dict(self.constraints),
			'project_id': self.project_id,
			'repo_root': self.repo_root,
		}


@dataclass(slots=True)
class FigmaSearchPlan:
	"""Provider routing + intelligence hints — query expansion lives in Community Intelligence."""

	seed_query: str = ''
	provider_ids: list[str] = field(default_factory=list)
	filters: dict[str, Any] = field(default_factory=dict)
	intelligence_hints: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'seed_query': self.seed_query,
			'provider_ids': list(self.provider_ids),
			'filters': dict(self.filters),
			'intelligence_hints': dict(self.intelligence_hints),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class PlannedCommunityQuery:
	"""One ranked semantic search for Figma Community."""

	text: str
	confidence: float
	pass_number: int = 1
	intent_label: str = 'primary'
	expansion_kind: str = 'seed'
	execute: bool = True

	def to_dict(self) -> dict[str, Any]:
		return {
			'text': self.text,
			'confidence': self.confidence,
			'pass_number': self.pass_number,
			'intent_label': self.intent_label,
			'expansion_kind': self.expansion_kind,
			'execute': self.execute,
		}


@dataclass(slots=True)
class CommunitySearchPlan:
	"""Community Intelligence output — many ranked searches before provider calls."""

	seed_query: str = ''
	page_types: list[str] = field(default_factory=list)
	industries: list[str] = field(default_factory=list)
	styles: list[str] = field(default_factory=list)
	design_languages: list[str] = field(default_factory=list)
	components: list[str] = field(default_factory=list)
	planned_queries: list[PlannedCommunityQuery] = field(default_factory=list)
	executable_queries: list[PlannedCommunityQuery] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'seed_query': self.seed_query,
			'page_types': list(self.page_types),
			'industries': list(self.industries),
			'styles': list(self.styles),
			'design_languages': list(self.design_languages),
			'components': list(self.components),
			'planned_queries': [q.to_dict() for q in self.planned_queries],
			'executable_queries': [q.to_dict() for q in self.executable_queries],
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class CandidateProfile:
	"""Normalized candidate intelligence — scored without re-opening Figma files."""

	industry: list[str] = field(default_factory=list)
	page_type: list[str] = field(default_factory=list)
	components: list[str] = field(default_factory=list)
	framework: str | None = None
	style: list[str] = field(default_factory=list)
	design_language: list[str] = field(default_factory=list)
	complexity: str = 'unknown'  # simple | moderate | complex | unknown
	patterns: list[str] = field(default_factory=list)
	confidence: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'industry': list(self.industry),
			'page_type': list(self.page_type),
			'components': list(self.components),
			'framework': self.framework,
			'style': list(self.style),
			'design_language': list(self.design_language),
			'complexity': self.complexity,
			'patterns': list(self.patterns),
			'confidence': self.confidence,
		}


@dataclass(slots=True)
class FigmaCandidate:
	"""Community or file candidate — rich profile for scoring without extraction."""

	candidate_id: str
	title: str
	source: str  # community | file | library
	provider_id: str
	file_key: str = ''
	node_id: str = ''
	url: str = ''
	tags: list[str] = field(default_factory=list)
	preview_ref: str = ''
	metadata: dict[str, Any] = field(default_factory=dict)
	profile: CandidateProfile = field(default_factory=CandidateProfile)
	discovery_score: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate_id': self.candidate_id,
			'title': self.title,
			'source': self.source,
			'provider_id': self.provider_id,
			'file_key': self.file_key,
			'node_id': self.node_id,
			'url': self.url,
			'tags': list(self.tags),
			'preview_ref': self.preview_ref,
			'metadata': dict(self.metadata),
			'profile': self.profile.to_dict(),
			'discovery_score': self.discovery_score,
		}


@dataclass(slots=True)
class FigmaRankedCandidate:
	"""Candidate after multi-intelligence ranking."""

	candidate: FigmaCandidate
	inspiration_score: float = 0.0
	consistency_fit: float = 0.0
	component_reuse_score: float = 0.0
	design_quality_score: float = 0.0
	framework_fit: float = 0.0
	overall_score: float = 0.0
	rationale: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate': self.candidate.to_dict(),
			'inspiration_score': self.inspiration_score,
			'consistency_fit': self.consistency_fit,
			'component_reuse_score': self.component_reuse_score,
			'design_quality_score': self.design_quality_score,
			'framework_fit': self.framework_fit,
			'overall_score': self.overall_score,
			'rationale': self.rationale,
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class FigmaDiscoveryRequest:
	"""Facade input for discovery pipeline."""

	query: str
	intent: FigmaIntentKind | None = None
	repo_root: str = ''
	project_id: str = 'default'
	max_candidates: int = 12
	provider_preference: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'intent': self.intent.value if self.intent else None,
			'repo_root': self.repo_root,
			'project_id': self.project_id,
			'max_candidates': self.max_candidates,
			'provider_preference': self.provider_preference,
		}


@dataclass(slots=True)
class FigmaDiscoveryResult:
	"""Output after discovery + ranking + selection planning (pre-extraction)."""

	intent: FigmaIntent
	search_plan: FigmaSearchPlan
	community_plan: CommunitySearchPlan
	candidates: list[FigmaRankedCandidate] = field(default_factory=list)
	selection_plan: Any = None  # SelectionPlan — avoid circular import in type hint
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		selection = self.selection_plan.to_dict() if self.selection_plan is not None else None
		return {
			'intent': self.intent.to_dict(),
			'search_plan': self.search_plan.to_dict(),
			'community_plan': self.community_plan.to_dict(),
			'candidates': [c.to_dict() for c in self.candidates],
			'selection_plan': selection,
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class FigmaExtractionResult:
	"""Raw + normalized design data from a provider."""

	candidate_id: str
	provider_id: str
	raw_payload: dict[str, Any] = field(default_factory=dict)
	tokens: list[dict[str, Any]] = field(default_factory=list)
	components: list[dict[str, Any]] = field(default_factory=list)
	variables: list[dict[str, Any]] = field(default_factory=list)
	patterns: list[dict[str, Any]] = field(default_factory=list)
	screenshot_refs: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate_id': self.candidate_id,
			'provider_id': self.provider_id,
			'tokens_count': len(self.tokens),
			'components_count': len(self.components),
			'variables_count': len(self.variables),
			'patterns_count': len(self.patterns),
			'screenshot_refs': list(self.screenshot_refs),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class FigmaPipelineResult:
	"""End-to-end pipeline result."""

	discovery: FigmaDiscoveryResult
	extractions: list[FigmaExtractionResult] = field(default_factory=list)
	deep_reviews: list[Any] = field(default_factory=list)  # DeepReviewResult
	reference_registry_ids: list[str] = field(default_factory=list)
	pdg_ingest_ready: bool = False
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		reviews = [r.to_dict() for r in self.deep_reviews if hasattr(r, 'to_dict')]
		return {
			'discovery': self.discovery.to_dict(),
			'extractions': [e.to_dict() for e in self.extractions],
			'deep_reviews': reviews,
			'reference_registry_ids': list(self.reference_registry_ids),
			'pdg_ingest_ready': self.pdg_ingest_ready,
			'degraded': list(self.degraded),
		}
