"""SEO Intelligence data models — stable contracts (architecture phase)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SeoProviderId(str, Enum):
	SEARCH_CONSOLE = 'search-console'
	ANALYTICS_GA4 = 'analytics-ga4'
	BING_WEBMASTER = 'bing-webmaster'
	LIBRECRAWL = 'librecrawl'
	LIGHTHOUSE = 'lighthouse'
	BROWSER = 'browser'


class SeoEvidenceKind(str, Enum):
	SEARCH_QUERY = 'search_query'
	INDEX_STATUS = 'index_status'
	CRAWL_ISSUE = 'crawl_issue'
	CORE_WEB_VITAL = 'core_web_vital'
	TRAFFIC_METRIC = 'traffic_metric'
	TECHNICAL_ISSUE = 'technical_issue'
	RENDERING_ISSUE = 'rendering_issue'
	SCHEMA = 'schema'
	INTERNAL_LINK = 'internal_link'
	PERFORMANCE = 'performance'
	OPPORTUNITY = 'opportunity'


class SeoConnectionStatus(str, Enum):
	NOT_CONFIGURED = 'not_configured'
	PENDING_AUTH = 'pending_auth'
	CONNECTED = 'connected'
	DEGRADED = 'degraded'
	ERROR = 'error'


class SeoVerificationStatus(str, Enum):
	PENDING = 'pending'
	PASSED = 'passed'
	FAILED = 'failed'
	SKIPPED = 'skipped'


@dataclass(slots=True)
class SeoProviderMeta:
	provider_id: str
	display_name: str
	priority_tier: int
	auth_required: bool
	user_owned_data: bool
	free_tier: bool
	capabilities: list[str] = field(default_factory=list)
	auth_notes: str = ''
	rate_limit_notes: str = ''
	official_docs_url: str = ''
	implementation_status: str = 'research'

	def to_dict(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'display_name': self.display_name,
			'priority_tier': self.priority_tier,
			'auth_required': self.auth_required,
			'user_owned_data': self.user_owned_data,
			'free_tier': self.free_tier,
			'capabilities': list(self.capabilities),
			'auth_notes': self.auth_notes,
			'rate_limit_notes': self.rate_limit_notes,
			'official_docs_url': self.official_docs_url,
			'implementation_status': self.implementation_status,
		}


@dataclass(slots=True)
class SeoEvidenceRef:
	"""Normalized evidence from any provider — never raw provider payloads in recommendations."""

	evidence_id: str
	provider_id: str
	kind: SeoEvidenceKind
	title: str
	summary: str
	url: str = ''
	page_url: str = ''
	metric_value: float | None = None
	metric_unit: str = ''
	severity: str = 'info'
	source_ref: str = ''
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'evidence_id': self.evidence_id,
			'provider_id': self.provider_id,
			'kind': self.kind.value,
			'title': self.title,
			'summary': self.summary,
			'url': self.url,
			'page_url': self.page_url,
			'metric_value': self.metric_value,
			'metric_unit': self.metric_unit,
			'severity': self.severity,
			'source_ref': self.source_ref,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class SeoRecommendation:
	"""Evidence-based recommendation — every claim must cite evidence_ids."""

	recommendation_id: str
	title: str
	summary: str
	priority: str
	category: str
	evidence_ids: list[str] = field(default_factory=list)
	fix_guidance: str = ''
	verification_steps: list[str] = field(default_factory=list)
	confidence: float = 0.0
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'recommendation_id': self.recommendation_id,
			'title': self.title,
			'summary': self.summary,
			'priority': self.priority,
			'category': self.category,
			'evidence_ids': list(self.evidence_ids),
			'fix_guidance': self.fix_guidance,
			'verification_steps': list(self.verification_steps),
			'confidence': self.confidence,
			'metadata': dict(self.metadata),
		}


@dataclass(slots=True)
class SeoAuditRequest:
	website_url: str
	property_url: str = ''
	repo_root: str = ''
	scan_id: str = ''
	providers: list[str] = field(default_factory=list)
	include_cross_analysis: bool = True
	include_recommendations: bool = True
	commercial_site: bool = True

	def to_dict(self) -> dict[str, Any]:
		return {
			'website_url': self.website_url,
			'property_url': self.property_url,
			'repo_root': self.repo_root,
			'scan_id': self.scan_id,
			'providers': list(self.providers),
			'include_cross_analysis': self.include_cross_analysis,
			'include_recommendations': self.include_recommendations,
			'commercial_site': self.commercial_site,
		}


@dataclass(slots=True)
class SeoAuditResult:
	request: SeoAuditRequest
	evidence: list[SeoEvidenceRef] = field(default_factory=list)
	recommendations: list[SeoRecommendation] = field(default_factory=list)
	providers_queried: list[str] = field(default_factory=list)
	connections: dict[str, str] = field(default_factory=dict)
	cross_analysis: list[dict[str, Any]] = field(default_factory=list)
	verification: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)
	graph_summary: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		return {
			'request': self.request.to_dict(),
			'evidence': [e.to_dict() for e in self.evidence],
			'recommendations': [r.to_dict() for r in self.recommendations],
			'providers_queried': list(self.providers_queried),
			'connections': dict(self.connections),
			'cross_analysis': list(self.cross_analysis),
			'verification': dict(self.verification),
			'degraded': list(self.degraded),
			'graph_summary': dict(self.graph_summary),
		}
