"""Component Intelligence models — normalized search schema."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ParsedQuery:
	"""Structured representation of a natural-language component search."""

	raw: str
	keywords: list[str] = field(default_factory=list)
	component_types: list[str] = field(default_factory=list)
	page_types: list[str] = field(default_factory=list)
	page_context: list[str] = field(default_factory=list)
	styles: list[str] = field(default_factory=list)
	animations: list[str] = field(default_factory=list)
	theme: str | None = None
	modifiers: list[str] = field(default_factory=list)
	audience: list[str] = field(default_factory=list)
	search_hints: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'raw': self.raw,
			'keywords': list(self.keywords),
			'component_types': list(self.component_types),
			'page_types': list(self.page_types),
			'page_context': list(self.page_context),
			'styles': list(self.styles),
			'animations': list(self.animations),
			'theme': self.theme,
			'modifiers': list(self.modifiers),
			'audience': list(self.audience),
			'search_hints': list(self.search_hints),
		}


@dataclass(slots=True)
class PlannedQuery:
	"""One query string in a search plan, ordered by confidence."""

	text: str
	confidence: float
	pass_number: int
	intent: str = 'primary'

	def to_dict(self) -> dict[str, Any]:
		return {
			'text': self.text,
			'confidence': self.confidence,
			'pass_number': self.pass_number,
			'intent': self.intent,
		}


@dataclass(slots=True)
class SearchPlan:
	"""Search strategy — generated deterministically or supplied by the host agent."""

	primary_intent: str
	parsed: ParsedQuery
	component_types: list[str] = field(default_factory=list)
	alternative_terminology: list[str] = field(default_factory=list)
	style_keywords: list[str] = field(default_factory=list)
	theme: str | None = None
	page_context: list[str] = field(default_factory=list)
	suggested_providers: list[str] = field(default_factory=list)
	suggested_registries: list[str] = field(default_factory=list)
	planned_queries: list[PlannedQuery] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'primary_intent': self.primary_intent,
			'parsed': self.parsed.to_dict(),
			'component_types': list(self.component_types),
			'alternative_terminology': list(self.alternative_terminology),
			'style_keywords': list(self.style_keywords),
			'theme': self.theme,
			'page_context': list(self.page_context),
			'suggested_providers': list(self.suggested_providers),
			'suggested_registries': list(self.suggested_registries),
			'planned_queries': [q.to_dict() for q in self.planned_queries],
		}

	def queries_for_pass(self, pass_number: int) -> list[PlannedQuery]:
		return [q for q in self.planned_queries if q.pass_number == pass_number]

	@classmethod
	def from_dict(cls, raw: dict[str, Any], *, fallback_parsed: ParsedQuery) -> SearchPlan:
		parsed_raw = raw.get('parsed') or {}
		parsed = ParsedQuery(
			raw=str(parsed_raw.get('raw') or fallback_parsed.raw),
			keywords=list(parsed_raw.get('keywords') or fallback_parsed.keywords),
			component_types=list(parsed_raw.get('component_types') or fallback_parsed.component_types),
			page_types=list(parsed_raw.get('page_types') or fallback_parsed.page_types),
			page_context=list(parsed_raw.get('page_context') or fallback_parsed.page_context),
			styles=list(parsed_raw.get('styles') or fallback_parsed.styles),
			animations=list(parsed_raw.get('animations') or fallback_parsed.animations),
			theme=parsed_raw.get('theme', fallback_parsed.theme),
			modifiers=list(parsed_raw.get('modifiers') or fallback_parsed.modifiers),
			audience=list(parsed_raw.get('audience') or fallback_parsed.audience),
			search_hints=list(parsed_raw.get('search_hints') or fallback_parsed.search_hints),
		)
		queries = [
			PlannedQuery(
				text=str(item.get('text') or ''),
				confidence=float(item.get('confidence') or 0.5),
				pass_number=int(item.get('pass_number') or 1),
				intent=str(item.get('intent') or 'primary'),
			)
			for item in (raw.get('planned_queries') or [])
			if isinstance(item, dict) and item.get('text')
		]
		return cls(
			primary_intent=str(raw.get('primary_intent') or fallback_parsed.raw),
			parsed=parsed,
			component_types=list(raw.get('component_types') or parsed.component_types),
			alternative_terminology=list(raw.get('alternative_terminology') or []),
			style_keywords=list(raw.get('style_keywords') or parsed.styles),
			theme=raw.get('theme', parsed.theme),
			page_context=list(raw.get('page_context') or parsed.page_context),
			suggested_providers=list(raw.get('suggested_providers') or ['shadcn_ecosystem']),
			suggested_registries=list(raw.get('suggested_registries') or []),
			planned_queries=queries,
		)


@dataclass(slots=True)
class SearchContext:
	"""Execution context passed to providers for one search pass."""

	parsed: ParsedQuery
	plan: SearchPlan
	pass_number: int
	queries: list[PlannedQuery]

	def to_dict(self) -> dict[str, Any]:
		return {
			'pass_number': self.pass_number,
			'queries': [q.to_dict() for q in self.queries],
		}


@dataclass(slots=True)
class ComponentCandidate:
	"""Normalized component candidate from any provider."""

	id: str
	provider: str
	provider_group: str
	name: str
	title: str
	category: str
	description: str
	tags: list[str] = field(default_factory=list)
	preview: str | None = None
	install_method: str | None = None
	framework: str | None = None
	source: str | None = None
	registry: str | None = None
	item_type: str | None = None
	relevance_score: float = 0.0
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'id': self.id,
			'provider': self.provider,
			'provider_group': self.provider_group,
			'name': self.name,
			'title': self.title,
			'category': self.category,
			'description': self.description,
			'tags': list(self.tags),
			'preview': self.preview,
			'install_method': self.install_method,
			'framework': self.framework,
			'source': self.source,
			'registry': self.registry,
			'item_type': self.item_type,
			'relevance_score': self.relevance_score,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class SearchSession:
	"""Debuggable record of one component search execution."""

	session_id: str
	original_request: str
	plan: SearchPlan
	passes_executed: list[int] = field(default_factory=list)
	queries_executed: list[dict[str, Any]] = field(default_factory=list)
	providers_searched: list[str] = field(default_factory=list)
	results_per_provider: dict[str, int] = field(default_factory=dict)
	latency_ms: dict[str, float] = field(default_factory=dict)
	total_latency_ms: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'session_id': self.session_id,
			'original_request': self.original_request,
			'plan': self.plan.to_dict(),
			'passes_executed': list(self.passes_executed),
			'queries_executed': list(self.queries_executed),
			'providers_searched': list(self.providers_searched),
			'results_per_provider': dict(self.results_per_provider),
			'latency_ms': dict(self.latency_ms),
			'total_latency_ms': self.total_latency_ms,
		}


@dataclass(slots=True)
class ComponentSearchResponse:
	query: ParsedQuery
	candidates: list[ComponentCandidate]
	search_plan: SearchPlan | None = None
	search_session: SearchSession | None = None
	providers_queried: list[str] = field(default_factory=list)
	provider_errors: dict[str, str] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		out: dict[str, Any] = {
			'query': self.query.to_dict(),
			'candidates': [c.to_dict() for c in self.candidates],
			'providers_queried': list(self.providers_queried),
			'provider_errors': dict(self.provider_errors),
			'degraded': list(self.degraded),
			'total': len(self.candidates),
		}
		if self.search_plan is not None:
			out['search_plan'] = self.search_plan.to_dict()
		if self.search_session is not None:
			out['search_session'] = self.search_session.to_dict()
		return out


@dataclass(slots=True)
class ComponentDetail:
	"""Full component metadata for get_component (future phases)."""

	candidate: ComponentCandidate
	files: list[dict[str, Any]] = field(default_factory=list)
	dependencies: list[str] = field(default_factory=list)
	raw: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate': self.candidate.to_dict(),
			'files': list(self.files),
			'dependencies': list(self.dependencies),
			'raw': dict(self.raw),
		}
