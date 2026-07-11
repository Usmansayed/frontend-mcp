"""Shared inspiration collection — used by CLI script and MCP handlers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.community_intelligence.planner import build_community_plan
from navigation.inspiration_intelligence.intent.parser import parse_intent
from navigation.inspiration_intelligence.models import InspirationSearchPlan
from navigation.inspiration_intelligence.planning.search_planner import DEFAULT_PROVIDER_PRIORITY
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore
from navigation.inspiration_intelligence.tools.downloader import download_manifest, slugify
from navigation.inspiration_intelligence.tools.media_urls import agent_view_url, normalize_image_url


@dataclass
class InspirationHit:
	provider_id: str
	candidate_id: str
	title: str
	url: str
	external_id: str
	preview_url: str = ''
	agent_view_url: str = ''
	screenshot_path: str = ''
	local_image: str = ''
	inspiration_blob: str = ''
	blob_session_id: str = ''
	blob_expires_at: str = ''
	fetch_tier: str = ''
	degraded: list[str] = field(default_factory=list)


async def collect_inspiration_hits(
	query: str,
	output_dir: Path | None = None,
	*,
	per_provider: int = 4,
	provider_ids: list[str] | None = None,
	download_images: bool = False,
	materialize_blobs: bool = True,
	blob_session_id: str | None = None,
	write_per_hit_files: bool = True,
) -> dict[str, Any]:
	"""Collect URL-first inspiration hits from gallery providers."""
	if output_dir is not None:
		output_dir.mkdir(parents=True, exist_ok=True)

	registry = InspirationProviderRegistry()
	intent = parse_intent(query)
	order = provider_ids or list(DEFAULT_PROVIDER_PRIORITY)
	search_plan = InspirationSearchPlan(seed_query=query, provider_ids=order)
	community_plan = build_community_plan(intent, search_plan)

	all_hits: list[InspirationHit] = []
	provider_summary: dict[str, object] = {}

	for provider_id in order:
		provider = registry.get(provider_id)
		if provider is None:
			continue
		provider_dir = (output_dir / provider_id) if output_dir is not None else None
		if provider_dir is not None:
			provider_dir.mkdir(exist_ok=True)

		try:
			candidates, degraded = await provider.discover_candidates(
				search_plan,
				community_plan=community_plan,
				intent=intent,
				max_results=per_provider,
			)
		except Exception as exc:
			provider_summary[provider_id] = {'count': 0, 'error': str(exc)}
			continue

		with_urls = 0
		for idx, candidate in enumerate(candidates, start=1):
			discovery_preview = normalize_image_url(candidate.preview_ref or '')
			preview_url = discovery_preview
			screenshot_path = ''
			fetch_tier = str(candidate.metadata.get('fetch_tier', ''))

			capture_deg: list[str] = []
			try:
				capture = await provider.capture_design(candidate, intent=intent)
				capture_deg = list(capture.degraded)
				for ref in capture.screenshot_refs:
					ref = normalize_image_url(ref)
					if not ref:
						continue
					if ref.startswith('http'):
						preview_url = ref
					elif Path(ref).is_file():
						screenshot_path = ref
						if not preview_url:
							preview_url = Path(ref).resolve().as_uri()
					break
			except Exception as exc:
				capture_deg = [f'capture_failed:{exc}']

			if not preview_url:
				preview_url = discovery_preview

			view_url = agent_view_url(
				page_url=candidate.url,
				preview_url=preview_url,
				screenshot_path=screenshot_path,
			)

			hit = InspirationHit(
				provider_id=provider_id,
				candidate_id=candidate.candidate_id,
				title=candidate.title,
				url=candidate.url,
				external_id=candidate.external_id,
				preview_url=preview_url,
				agent_view_url=view_url,
				screenshot_path=screenshot_path,
				fetch_tier=fetch_tier,
				degraded=list(degraded) + capture_deg,
			)
			if write_per_hit_files and provider_dir is not None:
				stem = f'{idx:02d}-{slugify(candidate.title)}'
				meta_path = provider_dir / f'{stem}.json'
				meta_path.write_text(json.dumps(asdict(hit), indent=2), encoding='utf-8')
			all_hits.append(hit)
			if view_url:
				with_urls += 1

		provider_summary[provider_id] = {
			'count': len(candidates),
			'with_urls': with_urls,
			'degraded': degraded[:8],
		}

	manifest: dict[str, Any] = {
		'query': query,
		'collected_at': datetime.now(timezone.utc).isoformat(),
		'output_dir': str(output_dir) if output_dir is not None else '',
		'mode': 'urls_first',
		'providers': order,
		'total_hits': len(all_hits),
		'total_with_urls': sum(1 for h in all_hits if h.agent_view_url),
		'provider_summary': provider_summary,
		'hits': [asdict(h) for h in all_hits],
	}

	manifest_path: Path | None = None
	if output_dir is not None:
		manifest_path = output_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

	blob_summary: dict[str, object] = {}
	if materialize_blobs and all_hits:
		store = InspirationBlobStore()
		session_id = blob_session_id or store.create_session(purpose=query)
		if manifest_path is not None:
			blob_summary = store.materialize_manifest(session_id, manifest_path)
			manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
		else:
			hits = list(manifest['hits'])
			blob_summary = store.materialize_hits(session_id, hits)
			manifest['hits'] = hits
			manifest['blob_session_id'] = session_id
			manifest['mode'] = 'urls_and_ephemeral_blobs'
			manifest['blob_summary'] = blob_summary

	if download_images and manifest_path is not None:
		download_manifest(manifest_path, output_dir)
		manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

	return manifest
