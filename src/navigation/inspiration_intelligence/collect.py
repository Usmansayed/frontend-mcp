"""Shared inspiration collection — used by CLI script and MCP handlers.

Image-first strategy:
  progressive queries → concurrent HTTP/CDN preview URLs → compress to ephemeral blobs
  Browser screenshots only as explicit fallback (allow_browser_screenshot / env).
  Stop at 3–5 high-quality image refs — quality over quantity.

Supports discover→collect reuse via candidate_urls / discover_token (no double cascade).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncio

from navigation.inspiration_intelligence.circuit import (
	filter_open_circuits,
	record_failure,
	record_success,
)
from navigation.inspiration_intelligence.community_intelligence.planner import build_community_plan
from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS
from navigation.inspiration_intelligence.discovery.concurrent_wave import discover_providers_concurrent
from navigation.inspiration_intelligence.intent.parser import parse_intent
from navigation.inspiration_intelligence.levels import levels_card, resolve_inspiration_level
from navigation.inspiration_intelligence.live_capture import (
	capture_famous_sites,
	should_run_live_sites,
)
from navigation.inspiration_intelligence.models import InspirationCandidate, InspirationSearchPlan
from navigation.inspiration_intelligence.multi_scout import multi_source_inspire, multi_source_inspire_parallel
from navigation.inspiration_intelligence.pattern_acquire import (
	acquire_pattern_inspiration,
	is_font_query,
)
from navigation.inspiration_intelligence.web_inspire import (
	acquire_web_inspiration,
	should_run_web_inspire,
)
from navigation.inspiration_intelligence.source_affinity import (
	affinity_key,
	prefer_categories_from_providers,
	prefer_providers,
	record_winners,
)
from navigation.inspiration_intelligence.parallel_queries import build_diverse_queries
from navigation.inspiration_intelligence.planning.progressive_search import (
	MIN_IMAGE_REFS,
	TARGET_IMAGE_REFS,
	has_enough_image_refs,
	has_enough_relevant_refs,
	image_ref_count,
	progressive_queries,
	resolve_collect_provider_order,
)
from navigation.inspiration_intelligence.planning.source_planner import build_source_plan
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.query_flex import (
	hit_relevance_score,
	is_relevant_hit,
	resolve_flexible_query,
)
from navigation.inspiration_intelligence.result_cache import (
	fingerprint,
	get_cached_hits,
	put_cached_hits,
)
from navigation.inspiration_intelligence.scout_cache import consume_discover_token
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
	source_kind: str = 'gallery_image'
	degraded: list[str] = field(default_factory=list)


def _preview_key(url: str) -> str:
	return normalize_image_url(url).split('?')[0].rstrip('/').lower()


def _candidates_from_reuse(
	*,
	candidate_urls: list[dict[str, Any]] | list[str] | None,
	discover_token: str | None,
) -> tuple[list[InspirationCandidate], list[str], str]:
	"""Build candidates from scout reuse inputs. Returns (cands, notes, reuse_mode)."""
	notes: list[str] = []
	raw_rows: list[dict[str, Any]] = []
	reuse_mode = ''

	if discover_token:
		cached = consume_discover_token(discover_token)
		if cached is None:
			notes.append('discover_token_miss')
		else:
			reuse_mode = 'discover_token'
			notes.append('reuse:discover_token')
			for row in cached.get('candidates') or []:
				if isinstance(row, dict):
					raw_rows.append(row)

	if candidate_urls:
		reuse_mode = reuse_mode or 'candidate_urls'
		notes.append('reuse:candidate_urls')
		for item in candidate_urls:
			if isinstance(item, str) and item.strip().startswith('http'):
				raw_rows.append({'preview_url': item.strip(), 'url': item.strip(), 'title': ''})
			elif isinstance(item, dict):
				raw_rows.append(item)

	cands: list[InspirationCandidate] = []
	seen: set[str] = set()
	for idx, row in enumerate(raw_rows):
		preview = normalize_image_url(
			str(row.get('preview_url') or row.get('preview_ref') or row.get('agent_view_url') or '')
		)
		page = str(row.get('url') or row.get('page_url') or preview or '')
		cid = str(row.get('candidate_id') or f'reuse:{idx}:{_preview_key(preview or page)}')
		if cid in seen:
			continue
		seen.add(cid)
		if not preview and not page:
			continue
		cands.append(
			InspirationCandidate(
				candidate_id=cid,
				title=str(row.get('title') or f'Reuse {idx + 1}'),
				source=str(row.get('provider_id') or row.get('source') or 'reuse'),
				provider_id=str(row.get('provider_id') or 'reuse'),
				external_id=str(row.get('external_id') or cid),
				url=page or preview,
				preview_ref=preview or page,
				metadata={'fetch_tier': 'reuse', 'source_kind': row.get('source_kind') or 'gallery_image'},
				discovery_score=float(row.get('discovery_score') or 0.85),
			)
		)
	return cands, notes, reuse_mode


async def _materialize_hit_from_candidate(
	*,
	provider: Any,
	provider_id: str,
	candidate: InspirationCandidate,
	intent: Any,
	allow_browser_screenshot: bool,
	q_text: str,
	provider_dir: Path | None,
	idx: int,
	write_per_hit_files: bool,
) -> InspirationHit | None:
	discovery_preview = normalize_image_url(candidate.preview_ref or '')
	preview_url = discovery_preview
	screenshot_path = ''
	fetch_tier = str(candidate.metadata.get('fetch_tier', ''))
	capture_deg: list[str] = []

	# CDN preview already on candidate: skip slow capture round-trip.
	if discovery_preview.startswith('http'):
		capture_deg = ['capture_tier:discovery_preview']
		preview_url = discovery_preview
	else:
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
	if not preview_url:
		return None

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
		source_kind=str(candidate.metadata.get('source_kind') or 'gallery_image'),
		degraded=capture_deg,
	)
	if write_per_hit_files and provider_dir is not None:
		stem = f'{idx:02d}-{slugify(candidate.title)}'
		meta_path = provider_dir / f'{stem}.json'
		meta_path.write_text(json.dumps(asdict(hit), indent=2), encoding='utf-8')
	return hit


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
	target_refs: int | None = None,
	min_refs: int | None = None,
	allow_browser_screenshot: bool = False,
	max_queries: int | None = None,
	mode: str | None = None,
	inspiration_level: str | None = None,
	candidate_urls: list[dict[str, Any]] | list[str] | None = None,
	discover_token: str | None = None,
	http_concurrency: int | None = None,
	include_live_sites: bool | None = None,
	live_capture_fn: Any | None = None,
	include_web_search: bool | None = None,
	max_web_screenshots: int | None = None,
	use_result_cache: bool = True,
	use_multi_scout: bool | None = None,
	multi_scout_fn: Any | None = None,
) -> dict[str, Any]:
	"""Collect image-first inspiration hits — concurrent HTTP wave + early cancel."""
	t_collect0 = time.perf_counter()
	if output_dir is not None:
		output_dir.mkdir(parents=True, exist_ok=True)

	level_plan = resolve_inspiration_level(inspiration_level, mode=mode)
	flex = resolve_flexible_query(query)
	# Soft-stop = early-exit hint for latency. NOT a hard cap on returned refs.
	soft_stop = int(target_refs) if target_refs is not None else level_plan.soft_stop_refs
	# Usable pack floor ≈ half soft_stop (standard→4, light→2). Do not hard-cap at 3 —
	# that caused soft_stop_multi_scout to exit page packs one short of a solid set.
	min_pack = int(min_refs) if min_refs is not None else max(1, soft_stop // 2)
	# Keep local names used throughout for early-cancel checks.
	target_refs = soft_stop
	min_refs = min_pack
	hunt_query = flex.search_query or query

	def _pack_ready(hits: list) -> bool:
		"""Usable pack for *this* ask — not any random gallery cards."""
		# Pattern/CDN specialists: soft-stop once we have a solid pack (speed path).
		# Count specialists only — web_search must not inflate this and skip itself.
		min_pattern = 3 if flex.scope in {'section', 'page'} else max(3, min(soft_stop, 4))
		if flex.scope in {'chrome', 'component', 'section', 'page'}:
			pattern_n = 0
			for hit in hits:
				tier = (
					str(hit.get('fetch_tier') or '')
					if isinstance(hit, dict)
					else str(getattr(hit, 'fetch_tier', '') or '')
				)
				kind = (
					str(hit.get('source_kind') or '')
					if isinstance(hit, dict)
					else str(getattr(hit, 'source_kind', '') or '')
				)
				if tier in {
					'direct_cdn',
					'pattern_http',
				} or kind in {
					'pattern_cdn',
					'pattern_gallery',
				}:
					pattern_n += 1
			if pattern_n >= min_pattern:
				return True
		# Auth/checkout soft-floor: need a real pack, not 1–2 junk cards
		intent_floor = 4 if flex.intent_class in {'auth', 'checkout'} else min_refs
		return has_enough_relevant_refs(
			hits,
			query=query,
			search_query=hunt_query,
			min_refs=max(min_refs, intent_floor) if flex.intent_class in {'auth', 'checkout'} else min_refs,
			target_refs=target_refs,
		)

	def _hit_score(hit: InspirationHit) -> float:
		return hit_relevance_score(
			query, title=hit.title, url=hit.url, search_query=hunt_query
		)

	def _accept_hit(hit: InspirationHit) -> bool:
		"""Page-scale: keep all. Fine grain: prefer query-matching cards."""
		if flex.scope == 'page':
			return True
		# Channel C search/screenshot hits already ranked by SERP — keep them
		if hit.source_kind in {'web_search', 'web_live'} or hit.fetch_tier in {
			'web_og',
			'web_live_screenshot',
		}:
			return True
		# Pattern/CDN companions (daisy bundles, specialist galleries) are intentional
		if hit.source_kind in {'pattern_cdn', 'pattern_gallery'} or hit.fetch_tier in {
			'direct_cdn',
			'pattern_http',
		}:
			return True
		min_score = 0.12 if flex.intent_class in {'auth', 'checkout'} else 0.18
		if is_relevant_hit(
			query,
			title=hit.title,
			url=hit.url,
			search_query=hunt_query,
			min_score=min_score,
		):
			return True
		# Auth/checkout thin pack: keep multi-scout CDN thumbs so soft-floor can fill
		if (
			flex.intent_class in {'auth', 'checkout'}
			and str(hit.fetch_tier or '').startswith('multi_scout')
			and hit.preview_url
			and image_ref_count(all_hits) < 4
		):
			return True
		# Allow a couple weak early so we never return empty before scout finishes
		return image_ref_count(all_hits) < 2

	def _try_add(hit: InspirationHit | None) -> bool:
		if hit is None:
			return False
		if not _accept_hit(hit):
			return False
		pkey = _preview_key(hit.preview_url) if hit.preview_url else ''
		if pkey and pkey in seen_previews:
			return False
		if pkey:
			seen_previews.add(pkey)
		all_hits.append(hit)
		return True

	# Map level → legacy mode for source_plan taxonomy
	# wide uses broad planner but broad is now HTTP-only (+ siteinspire); breadth = multi-scout.
	mode_from_level = {
		'light': 'fast',
		'standard': 'fast',
		'wide': 'broad',
		'max': 'deep',
	}.get(level_plan.level, mode)
	effective_mode = mode or mode_from_level
	deadline_s = level_plan.hard_deadline_s

	def _past_deadline() -> bool:
		return (time.perf_counter() - t_collect0) >= deadline_s

	def _deadline_mono() -> float:
		"""Absolute monotonic deadline for live capture budget checks."""
		remaining = max(0.0, deadline_s - (time.perf_counter() - t_collect0))
		return time.monotonic() + remaining

	registry = InspirationProviderRegistry()
	intent = parse_intent(query)
	# Prefer flex intent when taxonomy has it (e.g. navigation)
	styles = list(intent.target_styles)
	if flex.intent_class and flex.intent_class not in styles:
		styles = [flex.intent_class, *styles]
	source_plan = build_source_plan(
		hunt_query,
		mode=effective_mode,
		target_styles=styles,
		provider_ids=provider_ids,
		intent_class_override=flex.intent_class if flex.intent_class != 'default' else None,
	)
	order = resolve_collect_provider_order(provider_ids)
	if provider_ids is None and (mode or inspiration_level):
		order = list(source_plan.provider_ids)

	# Hard strip WAF/Chromium galleries unless level/max (or explicit provider_ids pin).
	browser_excluded: list[str] = []
	if provider_ids is None and not level_plan.include_browser_galleries:
		browser_excluded = [p for p in order if p in BROWSER_HEAVY_PROVIDERS]
		order = [p for p in order if p not in BROWSER_HEAVY_PROVIDERS]
	elif provider_ids is None and level_plan.include_browser_galleries:
		# Cap: HTTP first, at most one browser-heavy (never peel dribbble first).
		http_part = [p for p in order if p not in BROWSER_HEAVY_PROVIDERS]
		browser_part = [p for p in order if p in BROWSER_HEAVY_PROVIDERS][:1]
		browser_excluded = [p for p in order if p in BROWSER_HEAVY_PROVIDERS][1:]
		order = http_part + browser_part

	# Light FAST: skip Behance (403 → Stealthy kills cold p50). Keep for standard+.
	if provider_ids is None and level_plan.level == 'light':
		order = [p for p in order if p != 'behance']

	# Skip providers with open circuits (recent repeated failures).
	order, circuit_skipped = filter_open_circuits(order)

	concurrency = (
		http_concurrency
		if http_concurrency is not None
		else level_plan.http_concurrency
	)
	ladder_n = max_queries if max_queries is not None else level_plan.max_queries
	# Distinct parallel hunt strings (not progressive suffix expansion of one seed).
	queries = build_diverse_queries(flex, max_queries=max(1, ladder_n))
	if not queries:
		queries = progressive_queries(hunt_query, max_queries=ladder_n) or [hunt_query]
	queries = queries[:ladder_n]
	parallel_queries = list(queries)

	all_hits: list[InspirationHit] = []
	seen_candidates: set[str] = set()
	seen_previews: set[str] = set()
	provider_summary: dict[str, object] = {}
	queries_used: list[str] = []
	stopped_early = False
	stop_reason = ''
	timing_traces: list[dict[str, Any]] = []
	reuse_notes: list[str] = []
	reuse_mode = ''
	cache_hit = False
	multi_scout_meta: dict[str, Any] = {}
	pattern_meta: dict[str, Any] = {}
	scout_task: asyncio.Task | None = None
	run_multi = use_multi_scout
	if run_multi is None:
		run_multi = level_plan.use_multi_scout
	# Non-page asks need corpus/showcases — don't leave light on generic OPL only.
	# Light stays pattern/HTTP-fast: do not force multi-scout (cold-path budget).
	if (
		use_multi_scout is None
		and level_plan.level != 'light'
		and flex.scope in {'component', 'chrome', 'section'}
	):
		run_multi = True

	# --- Result cache BEFORE pattern/cascade (again-and-again path must be cheap) ---
	fp = fingerprint(f'{query}|{hunt_query}|{flex.scope}', mode=level_plan.level, provider_ids=order)
	if use_result_cache and not candidate_urls and not discover_token:
		cached = get_cached_hits(fp)
		if cached:
			cache_hit = True
			reuse_mode = 'result_cache'
			reuse_notes.append('reuse:result_cache')
			queries_used.append(query)
			for row in cached:
				preview = str(row.get('preview_url') or '')
				if not preview:
					continue
				pkey = _preview_key(preview)
				if pkey in seen_previews:
					continue
				seen_previews.add(pkey)
				cid = str(row.get('candidate_id') or pkey)
				seen_candidates.add(cid)
				all_hits.append(
					InspirationHit(
						provider_id=str(row.get('provider_id') or 'cache'),
						candidate_id=cid,
						title=str(row.get('title') or ''),
						url=str(row.get('url') or ''),
						external_id=str(row.get('external_id') or ''),
						preview_url=preview,
						agent_view_url=str(row.get('agent_view_url') or preview),
						screenshot_path=str(row.get('screenshot_path') or ''),
						fetch_tier='cache',
						search_query=query,
						source_kind=str(row.get('source_kind') or 'gallery_image'),
						degraded=['capture_tier:result_cache'],
					)
				)
			stopped_early = True
			stop_reason = 'result_cache'
			run_multi = False
			timing_traces.append(
				{
					'provider_id': '_result_cache',
					'elapsed_ms': round((time.perf_counter() - t_collect0) * 1000.0, 1),
					'ok': True,
					'count': len(all_hits),
				}
			)

	# --- Pattern path: specialist galleries + daisy CDN ---
	# Include page/landing so saasframe etc. beat Channel C on cold path.
	# Skip entirely on result-cache hit (warm MCP retries).
	if (
		not cache_hit
		and (
			flex.scope in {'component', 'chrome', 'section', 'page'}
			or is_font_query(query)
		)
	):
		try:
			pr = await acquire_pattern_inspiration(
				query,
				max_visuals=max(4, min(level_plan.scout_acquire, 10)),
				concurrency=max(4, level_plan.scout_concurrency or 6),
				timeout_s=min(2.5, max(1.0, level_plan.provider_timeout_s)),
			)
			pattern_meta = pr.to_dict()
			timing_traces.append(
				{
					'provider_id': '_pattern',
					'elapsed_ms': pr.elapsed_ms,
					'ok': bool(pr.hits) or bool(pr.font_route),
					'count': len(pr.hits),
					'targets': pr.targets,
				}
			)
			for row in pr.hits:
				cid = row.candidate_id
				if cid in seen_candidates:
					continue
				seen_candidates.add(cid)
				_try_add(
					InspirationHit(
						provider_id=row.provider_id,
						candidate_id=cid,
						title=row.title,
						url=row.url,
						external_id=cid,
						preview_url=row.preview_url,
						agent_view_url=row.preview_url,
						screenshot_path='',
						fetch_tier=row.fetch_tier,
						search_query=hunt_query,
						source_kind=row.source_kind,
						degraded=list(row.degraded)[:4],
					)
				)
			provider_summary['pattern'] = {
				'count': len(pr.targets),
				'with_urls': len(pr.hits),
				'font_route': pr.font_route,
			}
			if pr.font_route and not pr.hits:
				# Fonts: do not burn gallery cascade — return route hint
				stopped_early = True
				stop_reason = 'font_routed_to_resource_intelligence'
			elif _pack_ready(all_hits):
				# Light/standard: specialist pack is enough — stop hunting (cold speed).
				# Wide/max: keep hunting for variety under soft_stop.
				if level_plan.level in {'light', 'standard'}:
					stopped_early = True
					stop_reason = stop_reason or 'enough_relevant_refs_pattern'
		except Exception as exc:  # noqa: BLE001
			pattern_meta = {'error': str(exc)}
			timing_traces.append(
				{'provider_id': '_pattern', 'elapsed_ms': 0, 'ok': False, 'error': str(exc)}
			)

	# --- Channel C + optional overlapped multi-scout (wall ≈ max when both run) ---
	web_meta: dict[str, Any] = {}
	font_routed = stop_reason == 'font_routed_to_resource_intelligence'
	n_ss = (
		int(max_web_screenshots)
		if max_web_screenshots is not None
		else int(level_plan.max_web_screenshots)
	)
	if allow_browser_screenshot and n_ss < 2:
		n_ss = 2
	run_web = (
		(not font_routed)
		and (not _past_deadline())
		and (not stopped_early)
		and should_run_web_inspire(
			level=level_plan.level,
			hit_count=image_ref_count(all_hits),
			soft_stop_refs=soft_stop,
			include_web_search=(
				include_web_search
				if include_web_search is not None
				else level_plan.include_web_search
			),
			font_routed=font_routed,
		)
	)
	if (
		not run_web
		and not font_routed
		and not stopped_early
		and not _past_deadline()
		and include_web_search is not False
		and image_ref_count(all_hits) < 1
	):
		run_web = True

	# Pattern soft-stop (light/standard) + fonts + result-cache skip the slow gallery cascade.
	skip_cascade = cache_hit or stop_reason in {
		'font_routed_to_resource_intelligence',
		'enough_relevant_refs_pattern',
		'enough_relevant_refs_pattern_rescue',
		'result_cache',
	}

	async def _start_multi_scout(remaining: int):
		if multi_scout_fn is not None:
			return await multi_scout_fn(query)
		scout_mode = 'deep' if level_plan.level == 'max' else 'broad'
		aff_key = affinity_key(
			scope=flex.scope,
			intent_class=str(flex.intent_class or ''),
			query=query,
		)
		sticky = prefer_providers(aff_key)
		prefer_cats = list(flex.prefer_categories)
		for cat in prefer_categories_from_providers(sticky):
			if cat not in prefer_cats:
				prefer_cats.append(cat)
		scout_kwargs = dict(
			mode=scout_mode,
			max_sources=level_plan.max_sources or (8 if flex.scope != 'page' else 6),
			concurrency=max(1, level_plan.scout_concurrency or 8),
			timeout_s=max(0.4, level_plan.scout_timeout_s or 1.0),
			top_n=max(1, level_plan.top_n or 3),
			max_visuals=max(1, remaining),
			allow_screenshots=level_plan.allow_screenshots,
			capture_fn=live_capture_fn,
			early_cancel=True,
			prefer_categories=prefer_cats,
		)
		if len(parallel_queries) > 1:
			return await multi_source_inspire_parallel(parallel_queries, **scout_kwargs)
		return await multi_source_inspire(hunt_query, **scout_kwargs)

	def _merge_web_result(wr: Any) -> None:
		nonlocal stopped_early, stop_reason, web_meta
		web_meta = wr.to_dict() if hasattr(wr, 'to_dict') else {}
		timing_traces.extend(getattr(wr, 'timing', None) or [])
		provider_summary['web_search'] = {
			'count': int(getattr(wr, 'search_hits', 0) or 0),
			'with_urls': len(getattr(wr, 'hits', None) or []),
			'og_hits': int(getattr(wr, 'og_hits', 0) or 0),
			'screenshot_hits': int(getattr(wr, 'screenshot_hits', 0) or 0),
			'search_query': str(getattr(wr, 'search_query', '') or ''),
		}
		for row in getattr(wr, 'hits', None) or []:
			cid = row.candidate_id
			if cid in seen_candidates:
				continue
			seen_candidates.add(cid)
			view = agent_view_url(
				page_url=row.url,
				preview_url=row.preview_url,
				screenshot_path=row.screenshot_path,
			)
			_try_add(
				InspirationHit(
					provider_id=row.provider_id,
					candidate_id=cid,
					title=row.title,
					url=row.url,
					external_id=cid,
					preview_url=row.preview_url,
					agent_view_url=view,
					screenshot_path=row.screenshot_path,
					fetch_tier=row.fetch_tier,
					search_query=str(getattr(wr, 'search_query', '') or ''),
					source_kind=row.source_kind,
					degraded=list(row.degraded)[:4],
				)
			)
		if _pack_ready(all_hits) and not stop_reason:
			stopped_early = True
			stop_reason = 'enough_relevant_refs_web'

	def _merge_multi_acquired(acquired: list[dict[str, Any]], *, remaining: int, thin_pack: bool) -> None:
		nonlocal stopped_early, stop_reason
		force_variety = level_plan.level in {'wide', 'max'}
		for row in acquired:
			# wide/max: keep absorbing winners until soft_stop, not just min_refs
			if thin_pack and _pack_ready(all_hits):
				if force_variety and image_ref_count(all_hits) < soft_stop:
					pass
				else:
					stopped_early = True
					stop_reason = stop_reason or 'soft_stop_multi_scout'
					break
			if not thin_pack and image_ref_count(all_hits) >= target_refs + max(0, remaining):
				stopped_early = True
				stop_reason = stop_reason or 'soft_stop_multi_scout'
				break
			cid = str(row.get('candidate_id') or '')
			if cid and cid in seen_candidates:
				continue
			if cid:
				seen_candidates.add(cid)
			preview = str(row.get('preview_url') or '')
			hit = InspirationHit(
				provider_id=str(row.get('provider_id') or 'multi_scout'),
				candidate_id=cid or f"multi:{_preview_key(preview)}",
				title=str(row.get('title') or ''),
				url=str(row.get('url') or ''),
				external_id=str(row.get('external_id') or ''),
				preview_url=preview,
				agent_view_url=str(row.get('agent_view_url') or preview),
				screenshot_path=str(row.get('screenshot_path') or ''),
				fetch_tier=str(row.get('fetch_tier') or 'multi_scout'),
				search_query=hunt_query,
				source_kind=str(row.get('source_kind') or 'gallery_image'),
				degraded=list(row.get('degraded') or [])[:4],
			)
			_try_add(hit)

	async def _web_empty_specialist_rescue() -> None:
		"""P1: when SERP is empty or auth/checkout under soft-floor, force specialists."""
		nonlocal pattern_meta, stopped_early, stop_reason
		if flex.intent_class not in {'auth', 'checkout'}:
			return
		if image_ref_count(all_hits) >= 4 or _past_deadline():
			return
		web_count = 0
		ws = provider_summary.get('web_search')
		if isinstance(ws, dict):
			web_count = int(ws.get('count') or 0)
		# Always rescue under soft-floor for these intents; mark web_empty when SERP blank
		try:
			pr = await acquire_pattern_inspiration(
				query,
				max_visuals=max(4, min(level_plan.scout_acquire, 10)),
				concurrency=max(4, level_plan.scout_concurrency or 6),
				timeout_s=min(2.5, max(1.0, level_plan.provider_timeout_s)),
			)
		except Exception as exc:  # noqa: BLE001
			pattern_meta = {
				**(pattern_meta if isinstance(pattern_meta, dict) else {}),
				'web_empty_rescue_error': str(exc),
			}
			return
		added = 0
		for row in pr.hits:
			cid = row.candidate_id
			if cid in seen_candidates:
				continue
			seen_candidates.add(cid)
			if _try_add(
				InspirationHit(
					provider_id=row.provider_id,
					candidate_id=cid,
					title=row.title,
					url=row.url,
					external_id=cid,
					preview_url=row.preview_url,
					agent_view_url=row.preview_url,
					screenshot_path='',
					fetch_tier=row.fetch_tier,
					search_query=hunt_query,
					source_kind=row.source_kind,
					degraded=list(row.degraded)[:4] + ['web_empty_rescue'],
				)
			):
				added += 1
		pattern_meta = {
			**(pattern_meta if isinstance(pattern_meta, dict) else {}),
			'web_empty_rescue': True,
			'web_empty_rescue_added': added,
			'web_was_empty': web_count == 0,
		}
		timing_traces.append(
			{
				'provider_id': '_pattern_rescue',
				'elapsed_ms': getattr(pr, 'elapsed_ms', 0),
				'ok': added > 0,
				'count': added,
				'reason': 'web_empty_or_soft_floor',
			}
		)
		if _pack_ready(all_hits):
			stopped_early = True
			stop_reason = stop_reason or 'enough_relevant_refs_pattern_rescue'

	# Early scout when pattern thin — overlap with web search for wall≈max
	early_scout_done = False
	wide_needs_variety = (
		level_plan.level in {'wide', 'max'}
		and image_ref_count(all_hits) < level_plan.soft_stop_refs
	)
	start_scout_early = bool(
		run_multi
		and level_plan.overlap_scout
		and not font_routed
		and not candidate_urls
		and not discover_token
		and not skip_cascade
		and (not _pack_ready(all_hits) or wide_needs_variety)
		and not _past_deadline()
	)

	if run_web or start_scout_early:
		web_coro = None
		if run_web:
			web_coro = acquire_web_inspiration(
				query,
				scope=flex.scope,
				max_search=max(4, level_plan.max_web_search),
				max_og=max(3, level_plan.max_web_og),
				max_screenshots=max(0, n_ss),
				og_concurrency=max(4, min(8, level_plan.http_concurrency or 6)),
				capture_fn=live_capture_fn,
				browser_concurrency=1,
				search_aliases=list(flex.search_aliases or ()),
				parallel_queries=parallel_queries,
				deadline_mono=_deadline_mono(),
			)
		if start_scout_early:
			scout_task = asyncio.create_task(_start_multi_scout(level_plan.scout_acquire))

		if web_coro is not None and scout_task is not None:
			wr_res, ms_res = await asyncio.gather(web_coro, scout_task, return_exceptions=True)
			scout_task = None  # consumed
			if isinstance(wr_res, Exception):
				web_meta = {'error': str(wr_res)}
				timing_traces.append(
					{'provider_id': '_web_search', 'elapsed_ms': 0, 'ok': False, 'error': str(wr_res)}
				)
			else:
				_merge_web_result(wr_res)
			if isinstance(ms_res, Exception):
				multi_scout_meta = {'error': str(ms_res)}
			else:
				multi_scout_meta = ms_res.to_dict() if hasattr(ms_res, 'to_dict') else {'raw': True}
				timing_traces.append(
					{
						'provider_id': '_multi_scout',
						'elapsed_ms': float(getattr(ms_res, 'scout_ms', 0) or 0),
						'ok': True,
						'overlapped_with_web': True,
					}
				)
				_merge_multi_acquired(
					list(getattr(ms_res, 'acquired', None) or multi_scout_meta.get('acquired') or []),
					remaining=max(1, soft_stop - image_ref_count(all_hits)),
					thin_pack=not _pack_ready(all_hits),
				)
				provider_summary['multi_scout'] = {
					'count': int(getattr(ms_res, 'probed', 0) or multi_scout_meta.get('probed') or 0),
					'with_urls': len(getattr(ms_res, 'acquired', None) or multi_scout_meta.get('acquired') or []),
					'winners': [
						w.get('source_id') if isinstance(w, dict) else getattr(w, 'source_id', None)
						for w in (getattr(ms_res, 'winners', None) or multi_scout_meta.get('winners') or [])
					],
					'overlapped_with_web': True,
				}
				early_scout_done = True
		elif web_coro is not None:
			try:
				wr = await web_coro
				_merge_web_result(wr)
			except Exception as exc:  # noqa: BLE001
				web_meta = {'error': str(exc)}
				timing_traces.append(
					{'provider_id': '_web_search', 'elapsed_ms': 0, 'ok': False, 'error': str(exc)}
				)
	# After early web+scout overlap: if we soft-stopped under soft_stop, keep hunting
	# (wide/max always; any level that still lacks a usable pack).
	if early_scout_done and image_ref_count(all_hits) < soft_stop:
		if level_plan.level in {'wide', 'max'} or not _pack_ready(all_hits):
			stopped_early = False
			if stop_reason == 'soft_stop_multi_scout':
				stop_reason = ''

	# P1 soft-floor / web-empty: force auth/checkout specialists when still thin
	if not font_routed and not _past_deadline():
		await _web_empty_specialist_rescue()

	def _need_more_refs() -> bool:
		"""Continue hunting when pack thin, or wide/max under soft_stop variety."""
		if _past_deadline():
			return False
		n = image_ref_count(all_hits)
		# P1 soft-floor: auth/checkout must not exit under 4 usable refs
		if flex.intent_class in {'auth', 'checkout'} and n < 4:
			return True
		if level_plan.level in {'wide', 'max'} and n < soft_stop:
			return True
		return not _pack_ready(all_hits)

	# Cache hit (resolved early) = do not re-cascade galleries / multi-scout
	if cache_hit:
		skip_cascade = True
		run_multi = False

	# Overlap corpus scout with HTTP cascade when level asks for it (wall ≈ max).
	# Skip if already started/finished during web overlap.
	if (
		run_multi
		and level_plan.overlap_scout
		and not early_scout_done
		and scout_task is None
		and not cache_hit
		and not candidate_urls
		and not discover_token
		and not skip_cascade
		and _need_more_refs()
		and not _past_deadline()
	):
		scout_task = asyncio.create_task(_start_multi_scout(level_plan.scout_acquire))

	# --- Scout reuse: skip gallery cascade when URLs already known ---
	if not skip_cascade and _need_more_refs() and not _past_deadline():
		reuse_cands, scout_notes, scout_mode = _candidates_from_reuse(
			candidate_urls=candidate_urls,
			discover_token=discover_token,
		)
		reuse_notes.extend(scout_notes)
		if scout_mode:
			reuse_mode = scout_mode
		if reuse_cands:
			queries_used.append(query)
			for idx, candidate in enumerate(reuse_cands, start=1):
				if _pack_ready(all_hits):
					stopped_early = True
					stop_reason = 'enough_image_refs'
					break
				if candidate.candidate_id in seen_candidates:
					continue
				pkey = _preview_key(candidate.preview_ref or '')
				if pkey and pkey in seen_previews:
					continue
				seen_candidates.add(candidate.candidate_id)
				if pkey:
					seen_previews.add(pkey)
				provider = registry.get(candidate.provider_id)
				# Synthetic reuse provider stub when missing
				if provider is None:

					class _ReuseStub:
						async def capture_design(self, cand, *, intent, allow_browser_screenshot=False):
							from navigation.inspiration_intelligence.models import InspirationCaptureResult

							_ = intent, allow_browser_screenshot
							return InspirationCaptureResult(
								candidate_id=cand.candidate_id,
								provider_id=cand.provider_id,
								screenshot_refs=[cand.preview_ref],
								degraded=['capture_tier:reuse_preview'],
							)

					provider = _ReuseStub()
				hit = await _materialize_hit_from_candidate(
					provider=provider,
					provider_id=candidate.provider_id,
					candidate=candidate,
					intent=intent,
					allow_browser_screenshot=False,
					q_text=query,
					provider_dir=None,
					idx=idx,
					write_per_hit_files=False,
				)
				if hit is None:
					continue
				all_hits.append(hit)
			if _pack_ready(all_hits):
				stopped_early = True
				stop_reason = stop_reason or 'enough_image_refs_reuse'
			timing_traces.append(
				{
					'provider_id': '_reuse',
					'elapsed_ms': round((time.perf_counter() - t_collect0) * 1000.0, 1),
					'ok': True,
					'count': len(all_hits),
					'reuse_mode': reuse_mode,
				}
			)

	# --- Concurrent cascade when reuse did not fill the pack ---
	if not skip_cascade and _need_more_refs() and not _past_deadline():

		async def _discover_for_query(q_text: str):
			if _past_deadline():
				return q_text, {}, [], []
			search_plan = InspirationSearchPlan(seed_query=q_text, provider_ids=order)
			community_plan = build_community_plan(intent, search_plan)
			wave_results, wave_traces, searched = await discover_providers_concurrent(
				registry,
				order,
				search_plan=search_plan,
				community_plan=community_plan,
				intent=intent,
				max_results=per_provider,
				http_concurrency=concurrency,
				should_stop=None,  # parallel waves merge after — no per-query early cancel
				provider_timeout_s=level_plan.provider_timeout_s,
			)
			return q_text, wave_results, wave_traces, searched

		async def _materialize_wave(
			q_text: str,
			wave_results: dict[str, tuple[list[Any], list[str]]],
			searched: list[str],
		) -> None:
			nonlocal stopped_early, stop_reason
			if q_text not in queries_used:
				queries_used.append(q_text)

			for provider_id in order:
				if provider_id not in wave_results:
					continue
				if not _need_more_refs():
					stopped_early = True
					stop_reason = stop_reason or 'enough_image_refs'
					break

				candidates, degraded = wave_results[provider_id]
				provider = registry.get(provider_id)
				if provider is None:
					continue
				provider_dir = (output_dir / provider_id) if output_dir is not None else None
				if provider_dir is not None:
					provider_dir.mkdir(exist_ok=True)

				if candidates:
					record_success(provider_id)
				elif any('timeout' in d or 'error' in d for d in degraded):
					record_failure(provider_id)
				elif not candidates:
					record_failure(provider_id)

				todo: list[tuple[int, Any]] = []
				for idx, candidate in enumerate(candidates, start=1):
					if candidate.candidate_id in seen_candidates:
						continue
					seen_candidates.add(candidate.candidate_id)
					todo.append((idx, candidate))

				async def _cap(idx: int, candidate: Any, *, _provider=provider, _pid=provider_id):
					return await _materialize_hit_from_candidate(
						provider=_provider,
						provider_id=_pid,
						candidate=candidate,
						intent=intent,
						allow_browser_screenshot=allow_browser_screenshot,
						q_text=q_text,
						provider_dir=provider_dir,
						idx=idx,
						write_per_hit_files=write_per_hit_files,
					)

				sem = asyncio.Semaphore(6)

				async def _bounded(idx: int, candidate: Any):
					async with sem:
						return await _cap(idx, candidate)

				captured = await asyncio.gather(*[_bounded(i, c) for i, c in todo])
				with_urls = 0
				for hit in captured:
					if hit is None:
						continue
					hit.degraded = list(degraded) + list(hit.degraded)
					if not _try_add(hit):
						continue
					if hit.agent_view_url:
						with_urls += 1
					if not _need_more_refs():
						stopped_early = True
						stop_reason = stop_reason or 'enough_relevant_refs'
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

			for pid in searched:
				provider_summary.setdefault(pid, {'count': 0, 'with_urls': 0})

		async def _cascade_sequential() -> None:
			nonlocal stopped_early, stop_reason
			for q_text in queries:
				if _past_deadline():
					stopped_early = True
					stop_reason = 'hard_deadline'
					break
				if not _need_more_refs():
					stopped_early = True
					stop_reason = stop_reason or 'enough_image_refs'
					break

				search_plan = InspirationSearchPlan(seed_query=q_text, provider_ids=order)
				community_plan = build_community_plan(intent, search_plan)

				def _stop_from_wave(wave_results: dict) -> bool:
					approx = list(all_hits)
					for _pid, (batch, _deg) in wave_results.items():
						for c in batch:
							preview = normalize_image_url(c.preview_ref or '')
							if preview.startswith('http'):
								approx.append(
									{
										'preview_url': preview,
										'title': getattr(c, 'title', '') or '',
										'url': getattr(c, 'url', '') or '',
									}
								)
					if _past_deadline():
						return True
					if level_plan.level in {'wide', 'max'} and image_ref_count(approx) < soft_stop:
						return False
					return _pack_ready(approx)

				wave_results, wave_traces, searched = await discover_providers_concurrent(
					registry,
					order,
					search_plan=search_plan,
					community_plan=community_plan,
					intent=intent,
					max_results=per_provider,
					http_concurrency=concurrency,
					should_stop=_stop_from_wave,
					provider_timeout_s=level_plan.provider_timeout_s,
				)
				timing_traces.extend(wave_traces)
				await _materialize_wave(q_text, wave_results, searched)
				if stopped_early:
					break

		async def _cascade_parallel() -> None:
			nonlocal stopped_early, stop_reason
			queries_used.extend([q for q in queries if q not in queries_used])
			timing_traces.append(
				{
					'provider_id': '_provider_wave',
					'parallel_queries': len(queries),
					'ok': True,
				}
			)
			waves = await asyncio.gather(
				*[_discover_for_query(q) for q in queries],
				return_exceptions=True,
			)
			for i, row in enumerate(waves):
				if isinstance(row, Exception):
					timing_traces.append(
						{
							'provider_id': '_provider_wave',
							'query': queries[i][:80],
							'ok': False,
							'error': str(row),
						}
					)
					continue
				q_text, wave_results, wave_traces, searched = row
				timing_traces.extend(wave_traces)
				await _materialize_wave(q_text, wave_results, searched)
				if not _need_more_refs():
					stopped_early = True
					stop_reason = stop_reason or 'enough_relevant_refs'
					break

		if len(queries) > 1:
			await _cascade_parallel()
		else:
			await _cascade_sequential()

	# --- Multi-source scout → rank → acquire (corpus concurrent probe) ---
	thin_pack = not _pack_ready(all_hits)
	force_variety = level_plan.level in {'wide', 'max'}
	# Wide/max variety uses the level's soft_stop_refs (not a lower caller target_refs hint)
	under_variety = force_variety and image_ref_count(all_hits) < level_plan.soft_stop_refs
	need_scout = bool(
		run_multi
		and (thin_pack or under_variety)
		and not skip_cascade
		and not early_scout_done
		and not _past_deadline()
	)
	if thin_pack or under_variety:
		remaining = max(1, min(level_plan.scout_acquire, max(1, soft_stop - image_ref_count(all_hits))))
	else:
		remaining = max(1, min(level_plan.scout_acquire, 4))

	if scout_task is not None:
		try:
			if not need_scout:
				scout_task.cancel()
				await asyncio.gather(scout_task, return_exceptions=True)
				multi_scout_meta = {'cancelled': 'pack_full_or_deadline'}
				timing_traces.append(
					{
						'provider_id': '_multi_scout',
						'elapsed_ms': 0,
						'ok': True,
						'cancelled': True,
					}
				)
			else:
				ms = await scout_task
				multi_scout_meta = ms.to_dict() if hasattr(ms, 'to_dict') else dict(ms)
				timing_traces.append(
					{
						'provider_id': '_multi_scout',
						'elapsed_ms': multi_scout_meta.get('scout_ms') or 0,
						'ok': bool(multi_scout_meta.get('acquired')),
						'probed': multi_scout_meta.get('probed'),
						'winners': [w.get('source_id') for w in (multi_scout_meta.get('winners') or [])],
						'overlapped': True,
					}
				)
				_merge_multi_acquired(
					list(multi_scout_meta.get('acquired') or []),
					remaining=remaining,
					thin_pack=thin_pack,
				)
				provider_summary['multi_scout'] = {
					'count': int(multi_scout_meta.get('probed') or 0),
					'with_urls': len(multi_scout_meta.get('acquired') or []),
					'winners': [w.get('source_id') for w in (multi_scout_meta.get('winners') or [])],
				}
		except Exception as exc:  # noqa: BLE001
			multi_scout_meta = {'error': str(exc)}
			timing_traces.append(
				{'provider_id': '_multi_scout', 'elapsed_ms': 0, 'ok': False, 'error': str(exc)}
			)
	elif need_scout:
		try:
			ms = await _start_multi_scout(remaining)
			multi_scout_meta = ms.to_dict() if hasattr(ms, 'to_dict') else dict(ms)
			timing_traces.append(
				{
					'provider_id': '_multi_scout',
					'elapsed_ms': multi_scout_meta.get('scout_ms') or 0,
					'ok': bool(multi_scout_meta.get('acquired')),
					'probed': multi_scout_meta.get('probed'),
					'winners': [w.get('source_id') for w in (multi_scout_meta.get('winners') or [])],
					'overlapped': False,
				}
			)
			_merge_multi_acquired(
				list(multi_scout_meta.get('acquired') or []),
				remaining=remaining,
				thin_pack=thin_pack,
			)
			provider_summary['multi_scout'] = {
				'count': int(multi_scout_meta.get('probed') or 0),
				'with_urls': len(multi_scout_meta.get('acquired') or []),
				'winners': [w.get('source_id') for w in (multi_scout_meta.get('winners') or [])],
			}
		except Exception as exc:  # noqa: BLE001
			multi_scout_meta = {'error': str(exc)}
			timing_traces.append(
				{'provider_id': '_multi_scout', 'elapsed_ms': 0, 'ok': False, 'error': str(exc)}
			)

	if _past_deadline() and not stop_reason:
		stopped_early = True
		stop_reason = 'hard_deadline'

	# Final soft-floor rescue after cascade/scout (auth/checkout)
	if not font_routed and not _past_deadline() and image_ref_count(all_hits) < 4:
		await _web_empty_specialist_rescue()

	# --- Channel B: famous-site live screenshots (exclusive browser queue) ---
	live_sites_used = False
	live_degraded: list[str] = []
	eff_live = include_live_sites if include_live_sites is not None else level_plan.include_live_sites
	if (not _past_deadline()) and should_run_live_sites(
		mode=source_plan.mode.value,
		channels=source_plan.channels if eff_live else ['gallery_image'],
		max_famous_sites=source_plan.max_famous_sites if eff_live else 0,
		gallery_ref_count=image_ref_count(all_hits),
		min_refs=min_refs,
		include_live_sites=bool(eff_live),
	):
		# Append live sites for diversity — never truncate gallery refs to "make room".
		# Cap famous-site attempts — Chromium is expensive / WAF-prone
		max_live = max(1, min(source_plan.max_famous_sites, 2)) if eff_live else 0
		if max_live > 0:
			live_sites_used = True
			live = await capture_famous_sites(
				source_plan.famous_categories,
				max_sites=max_live,
				browser_concurrency=max(1, source_plan.browser_concurrency or 1),
				capture_fn=live_capture_fn,
				focus_scope=flex.scope,
				deadline_mono=_deadline_mono(),
			)
			timing_traces.extend(live.timing)
			live_degraded.extend(live.degraded)
			provider_summary['famous_site'] = {
				'count': live.sites_attempted,
				'with_urls': len(live.hits),
				'degraded': live.degraded[:8],
			}
			for row in live.hits:
				cid = str(row.get('candidate_id') or '')
				if cid and cid in seen_candidates:
					continue
				if cid:
					seen_candidates.add(cid)
				preview = str(row.get('preview_url') or '')
				screenshot_path = str(row.get('screenshot_path') or '')
				pkey = _preview_key(preview or screenshot_path)
				if pkey and pkey in seen_previews:
					continue
				if pkey:
					seen_previews.add(pkey)
				view = agent_view_url(
					page_url=str(row.get('url') or ''),
					preview_url=preview,
					screenshot_path=screenshot_path,
				)
				all_hits.append(
					InspirationHit(
						provider_id='famous_site',
						candidate_id=cid or f"live_site:{row.get('external_id')}",
						title=str(row.get('title') or ''),
						url=str(row.get('url') or ''),
						external_id=str(row.get('external_id') or ''),
						preview_url=preview,
						agent_view_url=view,
						screenshot_path=screenshot_path,
						fetch_tier='live_site',
						search_query=query,
						source_kind='live_site',
						degraded=list(live.degraded[:4]),
					)
				)

	# No hard ref cap — soft_stop only ends the hunt early for latency.
	# Rank fine-grained packs so relevant cards surface first for the agent.
	if all_hits and flex.scope != 'page':
		all_hits.sort(key=_hit_score, reverse=True)

	# Sticky winners — boost specialists/scout sources that delivered this pack
	if all_hits and not font_routed:
		winners = []
		for h in all_hits:
			pid = h.provider_id
			if pid and pid not in winners and not pid.startswith('_'):
				winners.append(pid)
		record_winners(
			affinity_key(
				scope=flex.scope,
				intent_class=str(flex.intent_class or ''),
				query=query,
			),
			winners[:8],
		)

	# Warm fingerprint cache for frequent MCP retries (gallery hits only).
	if use_result_cache and not cache_hit and all_hits:
		put_cached_hits(
			fp,
			[
				{
					'candidate_id': h.candidate_id,
					'title': h.title,
					'url': h.url,
					'preview_url': h.preview_url,
					'agent_view_url': h.agent_view_url,
					'provider_id': h.provider_id,
					'external_id': h.external_id,
					'screenshot_path': h.screenshot_path,
					'source_kind': h.source_kind,
				}
				for h in all_hits
				if h.preview_url.startswith('http') or h.preview_url.startswith('file:')
			],
		)

	collect_ms = (time.perf_counter() - t_collect0) * 1000.0
	manifest: dict[str, Any] = {
		'query': query,
		'collected_at': datetime.now(timezone.utc).isoformat(),
		'output_dir': str(output_dir) if output_dir is not None else '',
		'mode': 'image_first_concurrent',
		'inspiration_mode': source_plan.mode.value,
		'inspiration_level': level_plan.level,
		'inspiration_level_plan': level_plan.to_dict(),
		'inspiration_levels_card': levels_card(),
		'query_flex': flex.to_dict(),
		'hunt_query': hunt_query,
		'pattern': pattern_meta,
		'web_inspire': web_meta,
		'source_plan': source_plan.to_dict(),
		'providers': order,
		'circuit_skipped': circuit_skipped,
		'browser_excluded': browser_excluded,
		'hard_deadline_s': deadline_s,
		'queries_used': queries_used,
		'progressive_ladder': queries,
		'parallel_queries': parallel_queries,
		'stopped_early': stopped_early,
		'stop_reason': stop_reason,
		'target_refs': target_refs,
		'soft_stop_refs': soft_stop,
		'ref_policy': 'soft_stop_only_no_hard_cap',
		'image_ref_count': image_ref_count(all_hits),
		'total_hits': len(all_hits),
		'total_with_urls': sum(1 for h in all_hits if h.agent_view_url),
		'provider_summary': provider_summary,
		'browser_fallback_used': allow_browser_screenshot,
		'provider_ms': timing_traces,
		'collect_ms': round(collect_ms, 1),
		'reuse_mode': reuse_mode,
		'reuse_notes': reuse_notes,
		'cache_hit': cache_hit,
		'http_concurrency': concurrency,
		'multi_scout': multi_scout_meta,
		'live_sites_used': live_sites_used,
		'live_site_degraded': live_degraded[:12],
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
			blob_summary = await store.materialize_manifest_async(session_id, manifest_path)
			manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
		else:
			hits = list(manifest['hits'])
			blob_summary = await store.materialize_hits_async(session_id, hits)
			manifest['hits'] = hits
			manifest['blob_session_id'] = session_id
			manifest['mode'] = 'image_first_ephemeral_blobs'
			manifest['blob_summary'] = blob_summary

	if download_images and manifest_path is not None:
		download_manifest(manifest_path, output_dir)
		manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

	return manifest
