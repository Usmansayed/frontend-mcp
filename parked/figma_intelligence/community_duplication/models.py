"""Community Duplication Pipeline models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.figma_intelligence.models import FigmaCandidate, FigmaExtractionResult


@dataclass(slots=True)
class DuplicationRequest:
	"""Input for duplicating one Community template into user Drafts."""

	candidate: FigmaCandidate
	content_id: str = ''
	community_url: str = ''
	session_cookie: str = ''
	pat: str = ''
	headless: bool = False
	timeout_s: float = 120.0
	prefer_api_duplicate: bool = True

	def to_dict(self) -> dict[str, Any]:
		return {
			'candidate_id': self.candidate.candidate_id,
			'title': self.candidate.title,
			'content_id': self.content_id,
			'community_url': self.community_url or self.candidate.url,
			'has_session_cookie': bool(self.session_cookie),
			'has_pat': bool(self.pat),
			'headless': self.headless,
			'timeout_s': self.timeout_s,
		}


@dataclass(slots=True)
class DuplicationResult:
	"""Outcome of Community → Drafts duplication."""

	content_id: str
	file_key: str = ''
	draft_url: str = ''
	method: str = ''  # api_hub_files_duplicate | browser_open_in_figma | preexisting_file_key
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'content_id': self.content_id,
			'file_key': self.file_key,
			'draft_url': self.draft_url,
			'method': self.method,
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class OfficialFilePayload:
	"""Normalized payload from official Figma REST APIs."""

	file_key: str
	document: dict[str, Any] = field(default_factory=dict)
	components: dict[str, Any] = field(default_factory=dict)
	styles: dict[str, Any] = field(default_factory=dict)
	variables: dict[str, Any] = field(default_factory=dict)
	metadata: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'file_key': self.file_key,
			'metadata': dict(self.metadata),
			'components_count': len(self.components),
			'styles_count': len(self.styles),
			'variables_count': len(self.variables if isinstance(self.variables, dict) else {}),
			'degraded': list(self.degraded),
		}


@dataclass(slots=True)
class DuplicationPipelineResult:
	"""End-to-end: duplicate → REST load → extraction + design snapshot."""

	duplication: DuplicationResult
	official: OfficialFilePayload | None = None
	extraction: FigmaExtractionResult | None = None
	design_snapshot: dict[str, Any] = field(default_factory=dict)
	reference_registry_id: str = ''
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'duplication': self.duplication.to_dict(),
			'official': self.official.to_dict() if self.official else None,
			'extraction': self.extraction.to_dict() if self.extraction else None,
			'design_snapshot_keys': list(self.design_snapshot.keys()),
			'reference_registry_id': self.reference_registry_id,
			'degraded': list(self.degraded),
		}
