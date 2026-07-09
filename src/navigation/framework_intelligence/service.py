"""Framework Intelligence service — detect, route to doc provider, normalize."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import FrameworkDocsCache
from .detector import detect_project
from .models import FrameworkKnowledgeResponse, ProjectMetadata
from .providers.documentation import DocumentationProvider, DocumentationProviderError
from .providers.grounded_docs import GroundedDocsProvider


class FrameworkIntelligenceService:
	def __init__(
		self,
		*,
		provider: DocumentationProvider | None = None,
		cache: FrameworkDocsCache | None = None,
	) -> None:
		self._provider = provider or GroundedDocsProvider()
		self._cache = cache or FrameworkDocsCache()

	def detect(self, repo_root: Path) -> ProjectMetadata:
		return detect_project(repo_root)

	async def fetch_docs(
		self,
		repo_root: Path,
		*,
		topic: str,
		metadata: ProjectMetadata | None = None,
		use_cache: bool = True,
	) -> FrameworkKnowledgeResponse:
		meta = metadata or self.detect(repo_root)
		degraded = list(meta.degraded)
		if not topic.strip():
			return FrameworkKnowledgeResponse(
				metadata=meta,
				topic=topic,
				provider=self._provider.name,
				library_id=None,
				content='',
				summary='Topic is required for documentation lookup.',
				degraded=degraded + ['topic_missing'],
			)
		if not meta.framework:
			return FrameworkKnowledgeResponse(
				metadata=meta,
				topic=topic,
				provider=self._provider.name,
				library_id=None,
				content='',
				summary='Could not detect a supported frontend framework in this project.',
				degraded=degraded + ['framework_not_detected'],
			)

		cache_key = self._cache.make_key(
			framework=meta.framework,
			framework_version=meta.framework_version or 'unknown',
			topic=topic,
		)
		version_key = meta.cache_version_key()
		if use_cache:
			cached = self._cache.get(cache_key, version_key=version_key)
			if cached is not None:
				return FrameworkKnowledgeResponse(
					metadata=meta,
					topic=topic,
					provider=str(cached.get('provider') or self._provider.name),
					library_id=cached.get('library_id'),
					content=str(cached.get('content') or ''),
					summary=str(cached.get('summary') or ''),
					citations=list(cached.get('citations') or []),
					cached=True,
					degraded=degraded,
				)

		try:
			doc = await self._provider.fetch_documentation(meta, topic=topic)
		except DocumentationProviderError as exc:
			code = str(exc).split(':', 1)[0]
			return FrameworkKnowledgeResponse(
				metadata=meta,
				topic=topic,
				provider=self._provider.name,
				library_id=None,
				content='',
				summary='Documentation provider request failed.',
				degraded=degraded + ['docs_provider_unavailable', code, str(exc)],
			)

		response = FrameworkKnowledgeResponse(
			metadata=meta,
			topic=topic,
			provider=doc.provider,
			library_id=doc.library_id,
			content=doc.content,
			summary=doc.summary,
			citations=list(doc.citations),
			cached=False,
			degraded=degraded,
		)
		if use_cache and doc.content.strip():
			self._cache.set(
				cache_key,
				version_key=version_key,
				value={
					'provider': response.provider,
					'library_id': response.library_id,
					'content': response.content,
					'summary': response.summary,
					'citations': response.citations,
				},
			)
		return response

	def agent_summary_from_response(self, response: FrameworkKnowledgeResponse) -> dict[str, Any]:
		meta = response.metadata
		return {
			'framework': meta.framework,
			'framework_version': meta.framework_version,
			'primary_package': meta.primary_package,
			'build_tool': meta.build_tool,
			'package_manager': meta.package_manager,
			'language': meta.language,
			'topic': response.topic,
			'provider': response.provider,
			'library_id': response.library_id,
			'summary': response.summary,
			'cached': response.cached,
			'blocking': [],
			'advisory': list(response.degraded),
		}
