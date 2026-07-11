"""End-to-end POC: Community search → duplicate → official REST → Design Snapshot."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')
load_dotenv()

_pat = os.environ.get('figma_pat', '').strip() or os.environ.get('FIGMA_PAT', '').strip()
if _pat:
	os.environ['FIGMA_ACCESS_TOKEN'] = _pat

from navigation.figma_intelligence.community_duplication.models import DuplicationRequest
from navigation.figma_intelligence.community_duplication.orchestrator import (
	CommunityDuplicationOrchestrator,
)
from navigation.figma_intelligence.discovery.community_adapter.backends.http import (
	HttpCommunityBackend,
)
from navigation.figma_intelligence.discovery.community_adapter.normalize import hit_to_candidate
from navigation.figma_intelligence.models import PlannedCommunityQuery


async def main() -> int:
	query = os.environ.get('FIGMA_DUP_POC_QUERY', 'saas dashboard')
	skip_dup = os.environ.get('FIGMA_PIPELINE_FILE_KEY', '').strip()
	headless = os.environ.get('FIGMA_DUP_HEADLESS', '0').strip() in {'1', 'true', 'yes'}

	print('=== Community Duplication Pipeline POC ===')
	print(f'query: {query}')
	print(f'pat_configured: {bool(_pat)}')
	print(f'session_cookie: {bool(os.environ.get("FIGMA_SESSION_COOKIE", "").strip())}')
	print(f'headless: {headless}')

	# 1. Community Search (no PAT)
	backend = HttpCommunityBackend()
	hits, search_degraded = await backend.search(
		PlannedCommunityQuery(text=query, confidence=1.0),
		max_results=5,
	)
	print(f'\n--- Search ---')
	print(f'hits: {len(hits)} degraded: {search_degraded[:4]}')
	if not hits:
		print('No search hits — aborting')
		return 1

	top = hits[0]
	candidate = hit_to_candidate(top)
	content_id = top.extra.get('content_id') or ''
	print(f'selected: {top.title!r}')
	print(f'content_id: {content_id}')
	print(f'community_url: {top.community_url}')

	# 2. Duplication + official REST + snapshot
	req = DuplicationRequest(
		candidate=candidate,
		content_id=content_id,
		community_url=top.community_url,
		pat=_pat,
		headless=headless,
		session_cookie=os.environ.get('FIGMA_SESSION_COOKIE', ''),
	)
	if skip_dup:
		candidate.file_key = skip_dup
		print(f'\n--- Skipping duplication (FIGMA_PIPELINE_FILE_KEY set) ---')

	orch = CommunityDuplicationOrchestrator()
	result = await orch.run(req)

	print('\n--- Duplication ---')
	print(json.dumps(result.duplication.to_dict(), indent=2))
	print('\n--- Official API ---')
	if result.official:
		print(json.dumps(result.official.to_dict(), indent=2))
	if result.extraction:
		print('\n--- Extraction ---')
		print(json.dumps(result.extraction.to_dict(), indent=2))
	print('\n--- Design Snapshot ---')
	print('keys:', list(result.design_snapshot.keys()))
	print('components:', len(result.design_snapshot.get('components', [])))
	print('tokens:', len(result.design_snapshot.get('tokens', [])))
	print('variables:', len(result.design_snapshot.get('variables', [])))
	print('reference_registry_id:', result.reference_registry_id)
	print(f'degraded ({len(result.degraded)}):', result.degraded[:15])

	if not result.duplication.file_key:
		print('\n--- Next steps ---')
		print('Set FIGMA_SESSION_COOKIE from logged-in browser, or log in during headed browser run.')
		print('Or set FIGMA_PIPELINE_FILE_KEY to an owned file key to test REST extraction only.')
		return 2

	if not result.extraction or not result.extraction.components and not result.extraction.tokens:
		print('\nREST extraction returned empty — check PAT scopes (file_content:read).')
		return 3

	return 0


if __name__ == '__main__':
	raise SystemExit(asyncio.run(main()))
