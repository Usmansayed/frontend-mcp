"""Shared inspiration collection — used by CLI script and MCP handlers.

Image-first strategy:
  progressive queries → HTTP/CDN preview URLs → compress to ephemeral blobs
  Browser screenshots only as explicit fallback (allow_browser_screenshot / env).
  Stop at 3–5 high-quality image refs — quality over quantity.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.community_intelligence.planner import build_community_plan
from navigation.inspiration_intelligence.intent.parser import parse_intent
from navigation.inspiration_intelligence.models import InspirationSearchPlan
from navigation.inspiration_intelligence.planning.progressive_search import (
	IMAGE_FIRST_PROVIDER_ORDER,
	MIN_IMAGE_REFS,
	TARGET_IMAGE_REFS,
	has_enough_image_refs,
	image_ref_count,
	progressive_queries,
)
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
	search_query: str = ''
	degraded: list[str] = field(default_factory=list)


def _preview_key(url: str) -> str:
	return normalize_image_url(url).split('?')[0].rstrip('/').lower()


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
	target_refs: int = TARGET_IMAGE_REFS,
	min_refs: int = MIN_IMAGE_REFS,
	allow_browser_screenshot: bool = False,
	max_queries: int = 5,
) -> dict[str, Any]:
	"""Collect image-first inspiration hits — stop when enough CDN/HTTP previews exist."""
	if output_dir is not None:
		output_dir.mkdir(parents=True, exist_ok=True)

	registry = InspirationProviderRegistry()
	intent = parse_intent(query)
	order = list(provider_ids) if provider_ids else list(IMAGE_FIRST_PROVIDER_ORDER)
	# Keep unknown providers last; prefer image-first known order when caller omits ids.
	if provider_ids is None:
		for pid in DEFAULT_PROVIDER_PRIORITY:
			if pid not in order:
				order.append(pid)

	queries = progressive_queries(query, max_queries=max_queries)
	if not queries:
		queries = [query]

	all_hits: list[InspirationHit] = []
	seen_candidates: set[str] = set()
	seen_previews: set[str] = set()
	provider_summary: dict[str, object] = {}
	queries_used: list[str] = []
	stopped_early = False
	stop_reason = ''

	for q_text in queries:
		if has_enough_image_refs(all_hits, min_refs=min_refs, target_refs=target_refs):
			stopped_early = True
			stop_reason = 'enough_image_refs'
			break

		queries_used.append(q_text)
		search_plan = InspirationSearchPlan(seed_query=q_text, provider_ids=order)
		community_plan = build_community_plan(intent, search_plan)

		for provider_id in order:
			if has_enough_image_refs(all_hits, min_refs=min_refs, target_refs=target_refs):
				stopped_early = True
				stop_reason = 'enough_image_refs'
				break

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
				prev = provider_summary.get(provider_id)
				if isinstance(prev, dict):
					prev['error'] = str(exc)
				else:
					provider_summary[provider_id] = {'count': 0, 'error': str(exc)}
				continue

			with_urls = 0
			for idx, candidate in enumerate(candidates, start=1):
				if candidate.candidate_id in seen_candidates:
					continue
				seen_candidates.add(candidate.candidate_id)

				discovery_preview = normalize_image_url(candidate.preview_ref or '')
				preview_url = discovery_preview
				screenshot_path = ''
				fetch_tier = str(candidate.metadata.get('fetch_tier', ''))

				capture_deg: list[str] = []
				try:
					capture = await provider.capture_design(
						candidate,
						intent=intent,
						allow_browser_screenshot=allow_browser_screenshot,
					)
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
				except TypeError:
					# Providers without allow_browser_screenshot kwarg
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
				except Exception as exc:
					capture_deg = [f'capture_failed:{exc}']

				if not preview_url:
					preview_url = discovery_preview

				pkey = _preview_key(preview_url) if preview_url else ''
				if pkey and pkey in seen_previews:
					continue
				if pkey:
					seen_previews.add(pkey)

				# Prefer compressed image URL for host vision when available.
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
					search_query=q_text,
					degraded=list(degraded) + capture_deg,
				)
				if write_per_hit_files and provider_dir is not None:
					stem = f'{idx:02d}-{slugify(candidate.title)}'
					meta_path = provider_dir / f'{stem}.json'
					meta_path.write_text(json.dumps(asdict(hit), indent=2), encoding='utf-8')
				all_hits.append(hit)
				if view_url:
					with_urls += 1

				if has_enough_image_refs(all_hits, min_refs=min_refs, target_refs=target_refs):
					stopped_early = True
					stop_reason = 'enough_image_refs'
					break

			summary = provider_summary.get(provider_id)
			if isinstance(summary, dict) and 'count' in summary:
				summary['count'] = int(summary.get('count') or 0) + len(candidates)
				summary['with_urls'] = int(summary.get('with_urls') or 0) + with_urls
			else:
				provider_summary[provider_id] = {
					'count': len(candidates),
					'with_urls': with_urls,
					'degraded': degraded[:8],
				}

		if stopped_early:
			break

	# Cap at target — never dump dozens of images to the host.
	if len(all_hits) > target_refs:
		all_hits = all_hits[:target_refs]
		stopped_early = True
		stop_reason = stop_reason or 'target_cap'

	manifest: dict[str, Any] = {
		'query': query,
		'collected_at': datetime.now(timezone.utc).isoformat(),
		'output_dir': str(output_dir) if output_dir is not None else '',
		'mode': 'image_first',
		'providers': order,
		'queries_used': queries_used,
		'progressive_ladder': queries,
		'stopped_early': stopped_early,
		'stop_reason': stop_reason,
		'target_refs': target_refs,
		'image_ref_count': image_ref_count(all_hits),
		'total_hits': len(all_hits),
		'total_with_urls': sum(1 for h in all_hits if h.agent_view_url),
		'provider_summary': provider_summary,
		'browser_fallback_used': allow_browser_screenshot,
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
			manifest['mode'] = 'image_first_ephemeral_blobs'
			manifest['blob_summary'] = blob_summary

	if download_images and manifest_path is not None:
		download_manifest(manifest_path, output_dir)
		manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

	return manifest
