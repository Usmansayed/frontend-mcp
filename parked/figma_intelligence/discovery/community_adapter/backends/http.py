"""Optional HTTP backend — configure when Community endpoint is known."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.models import PlannedCommunityQuery


SEARCH_RESOURCE_TYPES = (
	'design_template,figjam_template,slide_template,ui_kit,prototype,'
	'site_template,cooper_template_file,figmake_template,weave_workflow'
)
DEFAULT_SEARCH_URL = (
	'https://www.figma.com/api/search/resources?'
	'query={query}&price=all&creators=all&sort_by=relevancy&'
	f'resource_type={SEARCH_RESOURCE_TYPES}&session_id=unattributed&'
	'include_content=false&caller=search_page&include_full_category=false&'
	'include_tags=false&queryId=frontend-perception'
)


class HttpCommunityBackend:
	"""GET search against Figma Community REST endpoint — no PAT."""

	backend_id = 'http'

	def __init__(self, *, url_template: str | None = None) -> None:
		self._url_template = (
			url_template
			or os.environ.get('FIGMA_COMMUNITY_SEARCH_URL', '').strip()
			or DEFAULT_SEARCH_URL
		)

	def enabled(self) -> bool:
		return bool(self._url_template)

	async def search(
		self,
		query: PlannedCommunityQuery,
		*,
		max_results: int,
	) -> tuple[list[CommunityDiscoveryHit], list[str]]:
		if not self._url_template:
			return [], ['http_backend_not_configured']

		url = self._url_template.format(
			query=urllib.parse.quote(query.text),
			max_results=max_results,
		)
		try:
			req = urllib.request.Request(
				url,
				headers={
					'User-Agent': (
						'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
						'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
					),
					'Accept': 'application/json',
				},
			)
			with urllib.request.urlopen(req, timeout=20) as resp:
				payload = json.loads(resp.read().decode('utf-8'))
		except Exception as exc:
			return [], [f'http_backend_error:{type(exc).__name__}']

		hits = _parse_payload(payload, max_results=max_results)
		return hits, (['http_backend'] if hits else ['http_backend_empty'])


def _parse_payload(payload: object, *, max_results: int) -> list[CommunityDiscoveryHit]:
	"""Parse Figma `/api/search/resources` or generic list payloads."""
	if isinstance(payload, dict):
		meta = payload.get('meta')
		if isinstance(meta, dict) and isinstance(meta.get('results'), list):
			return _parse_search_results(meta['results'], max_results=max_results)
		raw = payload.get('results') or payload.get('items') or payload.get('data') or []
		items = raw if isinstance(raw, list) else []
	elif isinstance(payload, list):
		items = payload
	else:
		return []

	return _parse_flat_items(items, max_results=max_results)


def _parse_search_results(results: list[object], *, max_results: int) -> list[CommunityDiscoveryHit]:
	hits: list[CommunityDiscoveryHit] = []
	for row in results[:max_results]:
		if not isinstance(row, dict):
			continue
		model = row.get('model') if isinstance(row.get('model'), dict) else row
		if not isinstance(model, dict):
			continue
		content_id = str(model.get('content_id') or '')
		resource_id = str(model.get('id') or content_id or '')
		title = str(model.get('name') or '')
		if not resource_id or not title:
			continue
		creator = model.get('creator') if isinstance(model.get('creator'), dict) else {}
		hits.append(
			CommunityDiscoveryHit(
				hit_id=f'community:{resource_id}',
				title=title,
				description=str(model.get('description') or '')[:500],
				author=str(creator.get('handle') or creator.get('name') or ''),
				preview_image=str(model.get('thumbnail_url') or ''),
				community_url=str(model.get('community_rdp_url') or model.get('rdp_url') or ''),
				likes=model.get('like_count') if isinstance(model.get('like_count'), int) else None,
				downloads=model.get('user_count') if isinstance(model.get('user_count'), int) else None,
				source_backend='http',
				discovery_score=0.6,
				extra={'content_id': content_id, 'resource_id': resource_id, 'resource_type': model.get('resource_type')},
			)
		)
	return hits


def _parse_flat_items(items: list[object], *, max_results: int) -> list[CommunityDiscoveryHit]:
	hits: list[CommunityDiscoveryHit] = []
	for item in items[:max_results]:
		if not isinstance(item, dict):
			continue
		hit_id = str(item.get('id') or item.get('hit_id') or item.get('candidate_id') or '')
		title = str(item.get('title') or item.get('name') or '')
		if not hit_id or not title:
			continue
		hits.append(
			CommunityDiscoveryHit(
				hit_id=hit_id,
				title=title,
				description=str(item.get('description', '')),
				tags=[str(t) for t in item.get('tags', []) if t],
				author=str(item.get('author', '') or item.get('creator', '')),
				preview_image=str(item.get('preview_image', '') or item.get('thumbnail', '')),
				community_url=str(item.get('community_url', '') or item.get('url', '')),
				file_key=str(item.get('file_key', '') or item.get('fileKey', '')),
				likes=item.get('likes') if isinstance(item.get('likes'), int) else None,
				downloads=item.get('downloads') if isinstance(item.get('downloads'), int) else None,
				design_system=str(item.get('design_system', '')),
				source_backend='http',
				discovery_score=float(item.get('score', 0.5)),
			)
		)
	return hits
