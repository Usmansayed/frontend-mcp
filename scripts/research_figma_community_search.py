"""Research POC — Figma Community search via discovered REST endpoint.

Evidence from Browser Intelligence reverse-engineering (2026-07-11).
Run: python scripts/research_figma_community_search.py
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

SEARCH_ENDPOINT = 'https://www.figma.com/api/search/resources'

DEFAULT_RESOURCE_TYPES = (
	'design_template,figjam_template,slide_template,ui_kit,prototype,'
	'site_template,cooper_template_file,figmake_template,weave_workflow'
)


def search_community(
	query: str,
	*,
	resource_type: str = DEFAULT_RESOURCE_TYPES,
	page: int = 1,
	max_preview: int = 3,
) -> dict:
	params = {
		'query': query,
		'price': 'all',
		'creators': 'all',
		'sort_by': 'relevancy',
		'resource_type': resource_type,
		'session_id': 'unattributed',
		'include_content': 'false',
		'caller': 'search_page',
		'include_full_category': 'false',
		'include_tags': 'false',
		'queryId': f'frontend-perception-poc-{query.replace(" ", "-")}',
		'page': str(page),
	}
	url = f'{SEARCH_ENDPOINT}?{urllib.parse.urlencode(params)}'
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
	with urllib.request.urlopen(req, timeout=30) as resp:
		payload = json.loads(resp.read().decode('utf-8'))

	results = payload.get('meta', {}).get('results', [])
	total_hits = payload.get('meta', {}).get('total_hits')
	normalized = [_normalize_hit(row.get('model', {})) for row in results[:max_preview]]
	return {
		'query': query,
		'page': page,
		'total_hits': total_hits,
		'result_count': len(results),
		'preview': normalized,
	}


def _normalize_hit(model: dict) -> dict:
	creator = model.get('creator') or {}
	return {
		'resource_id': model.get('id'),
		'content_id': model.get('content_id'),
		'title': model.get('name'),
		'description': (model.get('description') or '')[:200],
		'resource_type': model.get('resource_type'),
		'community_url': model.get('community_rdp_url') or model.get('rdp_url'),
		'thumbnail_url': model.get('thumbnail_url'),
		'likes': model.get('like_count'),
		'uses': model.get('user_count'),
		'author': creator.get('handle') or creator.get('name'),
		'created_at': model.get('created_at'),
		'tags_v2': model.get('tags_v2'),
	}


def main() -> int:
	queries = ['dashboard', 'navbar', 'saas', 'pricing', 'login', 'landing page', 'analytics']
	sys.stdout.reconfigure(encoding='utf-8')
	print('=== Figma Community Search POC ===')
	print(f'endpoint: {SEARCH_ENDPOINT}\n')
	for q in queries:
		try:
			out = search_community(q)
			print(f"[{q!r}] total_hits={out['total_hits']} returned={out['result_count']}")
			for i, hit in enumerate(out['preview'], 1):
				print(
					f"  {i}. {hit['title'][:60]!r} "
					f"content_id={hit['content_id']} likes={hit['likes']} uses={hit['uses']}"
				)
		except Exception as exc:
			print(f'[{q!r}] ERROR {type(exc).__name__}: {exc}')
		print()
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
