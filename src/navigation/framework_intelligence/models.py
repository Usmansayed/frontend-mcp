"""Framework Intelligence models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectMetadata:
	repo_root: str
	framework: str | None = None
	framework_version: str | None = None
	primary_package: str | None = None
	build_tool: str | None = None
	package_manager: str | None = None
	language: str = 'javascript'
	is_monorepo: bool = False
	rendering_mode: str | None = None
	router_mode: str | None = None
	config_files: list[str] = field(default_factory=list)
	project_structure: dict[str, Any] = field(default_factory=dict)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'repo_root': self.repo_root,
			'framework': self.framework,
			'framework_version': self.framework_version,
			'primary_package': self.primary_package,
			'build_tool': self.build_tool,
			'package_manager': self.package_manager,
			'language': self.language,
			'is_monorepo': self.is_monorepo,
			'rendering_mode': self.rendering_mode,
			'router_mode': self.router_mode,
			'config_files': list(self.config_files),
			'project_structure': dict(self.project_structure),
			'degraded': list(self.degraded),
		}

	def cache_version_key(self) -> str:
		return f'{self.framework or "unknown"}:{self.framework_version or "unknown"}'


@dataclass(slots=True)
class DocumentationResult:
	"""Normalized documentation payload from any provider."""

	provider: str
	library_id: str
	title: str
	content: str
	summary: str
	citations: list[str] = field(default_factory=list)
	snippets: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'provider': self.provider,
			'library_id': self.library_id,
			'title': self.title,
			'content': self.content,
			'summary': self.summary,
			'citations': list(self.citations),
			'snippets': list(self.snippets),
		}


@dataclass(slots=True)
class FrameworkKnowledgeResponse:
	metadata: ProjectMetadata
	topic: str
	provider: str
	library_id: str | None
	content: str
	summary: str
	citations: list[str] = field(default_factory=list)
	cached: bool = False
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'metadata': self.metadata.to_dict(),
			'topic': self.topic,
			'provider': self.provider,
			'library_id': self.library_id,
			'content': self.content,
			'summary': self.summary,
			'citations': list(self.citations),
			'cached': self.cached,
			'degraded': list(self.degraded),
		}
