"""Community Duplication Pipeline orchestrator."""
from __future__ import annotations

import os

from navigation.figma_intelligence.community_duplication.api_loader import (
	FigmaRestClient,
	build_design_snapshot,
	load_official_file,
	official_to_extraction,
)
from navigation.figma_intelligence.community_duplication.browser import CommunityDuplicationBrowser
from navigation.figma_intelligence.community_duplication.duplication import duplicate_via_session_api
from navigation.figma_intelligence.community_duplication.file_key_resolver import (
	resolve_content_id,
)
from navigation.figma_intelligence.community_duplication.models import (
	DuplicationPipelineResult,
	DuplicationRequest,
	DuplicationResult,
)
from navigation.figma_intelligence.registry.reference_bridge import register_extractions


class CommunityDuplicationOrchestrator:
	"""Duplicate Community template → extract file_key → official REST → Design Snapshot."""

	async def run(self, request: DuplicationRequest) -> DuplicationPipelineResult:
		degraded: list[str] = []
		candidate = request.candidate

		if candidate.file_key:
			dup = DuplicationResult(
				content_id=resolve_content_id(url=candidate.url, metadata=candidate.metadata),
				file_key=candidate.file_key,
				draft_url=f'https://www.figma.com/design/{candidate.file_key}',
				method='preexisting_file_key',
			)
		else:
			dup, dup_degraded = await self._duplicate(request)
			degraded.extend(dup_degraded)

		if not dup.file_key:
			degraded.extend(d for d in dup.degraded if d not in degraded)
			return DuplicationPipelineResult(duplication=dup, degraded=degraded)

		pat = request.pat or FigmaRestClient.pat_from_env()
		if not pat:
			degraded.append('figma_pat_missing_for_rest_extraction')
			return DuplicationPipelineResult(duplication=dup, degraded=degraded)

		try:
			official = load_official_file(dup.file_key, pat=pat)
		except Exception as exc:
			degraded.append(f'official_api_load_failed:{type(exc).__name__}')
			return DuplicationPipelineResult(duplication=dup, degraded=degraded)

		extraction = official_to_extraction(official, candidate_id=candidate.candidate_id)
		extraction.degraded.extend(dup.degraded)
		snapshot = build_design_snapshot(extraction)

		ref_ids, reg_degraded = register_extractions([extraction], intent=_default_intent())
		degraded.extend(official.degraded)
		degraded.extend(reg_degraded)

		return DuplicationPipelineResult(
			duplication=dup,
			official=official,
			extraction=extraction,
			design_snapshot=snapshot,
			reference_registry_id=ref_ids[0] if ref_ids else '',
			degraded=degraded,
		)

	async def _duplicate(self, request: DuplicationRequest) -> tuple[DuplicationResult, list[str]]:
		degraded: list[str] = []
		content_id = (
			request.content_id
			or resolve_content_id(url=request.community_url or request.candidate.url, metadata=request.candidate.metadata)
		)
		if not content_id:
			return (
				DuplicationResult(content_id='', degraded=['content_id_missing']),
				['content_id_missing'],
			)

		community_url = request.community_url or request.candidate.url or f'https://www.figma.com/community/file/{content_id}'
		session_cookie = request.session_cookie or os.environ.get('FIGMA_SESSION_COOKIE', '').strip()

		if request.prefer_api_duplicate and session_cookie:
			dup, _payload = await duplicate_via_session_api(
				content_id,
				session_cookie=session_cookie,
				referer=community_url,
			)
			if dup.file_key:
				return dup, degraded + dup.degraded
			degraded.extend(dup.degraded)
			degraded.append('session_api_duplicate_fallback_to_browser')

		async with CommunityDuplicationBrowser(
			headless=request.headless,
			session_cookie=session_cookie,
			timeout_s=request.timeout_s,
		) as browser:
			dup, browser_degraded = await browser.duplicate_community_file(
				content_id=content_id,
				community_url=community_url,
			)
			degraded.extend(browser_degraded)
			return dup, degraded


def _default_intent():
	from navigation.figma_intelligence.intent.parser import parse_intent

	return parse_intent('community duplication pipeline')
