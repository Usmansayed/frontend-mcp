"""Inspiration Intelligence service facade."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.models import (
	InspirationDiscoveryRequest,
	InspirationDiscoveryResult,
	InspirationPipelineResult,
)
from navigation.inspiration_intelligence.planning.orchestrator import InspirationPipelineOrchestrator
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore
from navigation.inspiration_intelligence.tools.media_urls import normalize_image_url


class InspirationIntelligenceService:
	"""Orchestration layer for multi-provider design inspiration."""

	def __init__(self, providers: InspirationProviderRegistry | None = None) -> None:
		self._providers = providers or InspirationProviderRegistry()
		self._orchestrator = InspirationPipelineOrchestrator(self._providers)
		self._blob_store = InspirationBlobStore()

	async def discover(self, request: InspirationDiscoveryRequest) -> InspirationDiscoveryResult:
		return await self._orchestrator.discover(request)

	async def run_pipeline(
		self,
		request: InspirationDiscoveryRequest,
		*,
		materialize_blobs: bool | None = None,
		blob_session_id: str | None = None,
	) -> InspirationPipelineResult:
		result = await self._orchestrator.run_pipeline(request)
		if materialize_blobs is None:
			materialize_blobs = os.environ.get('INSPIRATION_BLOBS', '1') != '0'
		if materialize_blobs and result.captures:
			summary = self.materialize_pipeline_blobs(result, session_id=blob_session_id)
			result.degraded.append(f'blob_session:{summary.get("session_id", "")}')
		return result

	def materialize_pipeline_blobs(
		self,
		result: InspirationPipelineResult,
		*,
		session_id: str | None = None,
	) -> dict[str, Any]:
		"""Create ephemeral medium JPEGs from pipeline captures for agent vision."""
		candidate_by_id = {c.candidate.candidate_id: c.candidate for c in result.discovery.candidates}
		hits: list[dict[str, Any]] = []
		for capture in result.captures:
			candidate = candidate_by_id.get(capture.candidate_id)
			preview = ''
			screenshot_path = ''
			for ref in capture.screenshot_refs:
				ref = normalize_image_url(ref)
				if ref.startswith('http'):
					preview = ref
					break
				if ref and Path(ref).is_file():
					screenshot_path = ref
					preview = ref
					break
			if not preview and candidate is not None:
				preview = normalize_image_url(candidate.preview_ref or '')
			hits.append(
				{
					'preview_url': preview,
					'url': candidate.url if candidate else '',
					'provider_id': capture.provider_id,
					'candidate_id': capture.candidate_id,
					'title': candidate.title if candidate else capture.candidate_id,
					'screenshot_path': screenshot_path,
				}
			)
		sid = session_id or self._blob_store.create_session(
			purpose=result.discovery.intent.raw_query,
		)
		return self._blob_store.materialize_hits(sid, hits)

	def end_inspiration_session(self, session_id: str) -> dict[str, Any]:
		"""Delete ephemeral blobs for a session (call when agent work is done)."""
		removed = self._blob_store.end_session(session_id)
		return {'session_id': session_id, 'removed': removed}

	def cleanup_inspiration_blobs(self) -> dict[str, Any]:
		"""TTL safety net — remove expired blob sessions."""
		removed = self._blob_store.cleanup_expired()
		return {'expired_sessions_removed': removed}

	def list_inspiration_sessions(self) -> list[dict[str, Any]]:
		return self._blob_store.list_sessions()

	def list_providers(self) -> list[dict[str, object]]:
		return self._providers.list_providers()

	def status(self) -> dict[str, object]:
		return {
			'module': 'inspiration_intelligence',
			'phase': 'architecture_v1',
			'providers': self.list_providers(),
			'blob_sessions': len(self.list_inspiration_sessions()),
		}
