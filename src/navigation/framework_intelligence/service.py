"""Framework Intelligence service — detect, query provider, normalize."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import FrameworkDocsCache
from .detector import detect_project
from .models import FrameworkKnowledgeResponse, ProjectMetadata, ResolvedLibrary
from .providers.base import KnowledgeProvider
from .providers.context7 import Context7Provider, Context7Error


class FrameworkIntelligenceService:
	def __init__(
		self,
		*,
		provider: KnowledgeProvider | None = None,
		cache: FrameworkDocsCache | None = None,
	) -> None:
		self._provider = provider or Context7Provider()
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

		resolved: ResolvedLibrary | None
		content = ''
		try:
			resolved = await self._provider.resolve_library(meta, topic=topic)
			if resolved is None:
				return FrameworkKnowledgeResponse(
					metadata=meta,
					topic=topic,
					provider=self._provider.name,
					library_id=None,
					content='',
					summary=f'No documentation library found for {meta.framework}.',
					degraded=degraded + ['library_not_found'],
				)
			content = await self._provider.fetch_documentation(
				library_id=resolved.library_id,
				topic=topic,
				metadata=meta,
			)
		except Context7Error as exc:
			return FrameworkKnowledgeResponse(
				metadata=meta,
				topic=topic,
				provider=self._provider.name,
				library_id=None,
				content='',
				summary='Documentation provider request failed.',
				degraded=degraded + ['context7_unavailable', str(exc)],
			)

		summary = self._summarize(meta, topic, resolved, content)
		citations = [resolved.library_id]
		response = FrameworkKnowledgeResponse(
			metadata=meta,
			topic=topic,
			provider=resolved.provider,
			library_id=resolved.library_id,
			content=content,
			summary=summary,
			citations=citations,
			cached=False,
			degraded=degraded,
		)
		if use_cache and content.strip():
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

	def _summarize(
		self,
		meta: ProjectMetadata,
		topic: str,
		resolved: ResolvedLibrary,
		content: str,
	) -> str:
		words = len(content.split())
		framework = meta.framework or 'unknown'
		version = meta.framework_version or 'unknown'
		return (
			f'{framework} {version} docs for "{topic}" via {resolved.provider} '
			f'({resolved.library_id}); ~{words} words'
		)

	def agent_summary_from_response(self, response: FrameworkKnowledgeResponse) -> dict[str, Any]:
		meta = response.metadata
		return {
			'framework': meta.framework,
			'framework_version': meta.framework_version,
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
