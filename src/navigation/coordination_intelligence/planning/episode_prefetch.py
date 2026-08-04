"""Episode-scoped HTTP prefetch — parallelize intel behind the agent loop.

Invariants (see docs/research/2026-07-30-mcp-parallelism-architecture.md):
- Never touches the shared app browser / SessionStore.
- Heavy/very_heavy: full family warm (inspiration/component/creative_kit).
- Medium greenfield/redesign/mockup: light warm (creative_kit + inspiration).
- Hotfix/forms stay lean (no inspiration / creative_kit warm).
- Cancel on session_end; hard wall budget per family.
- Results are cache hints (discover_token, shortlists) — agents still call tools.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_SOFT_BUDGET_S = 2.0
_HARD_BUDGET_S = 8.0
_HEAVY_BANDS = frozenset({"heavy", "very_heavy"})
_CREATIVE_CLASSES = frozenset({"greenfield", "redesign"})
_MEDIUM_WARM_CLASSES = frozenset({"greenfield", "redesign", "mockup"})
_NO_GALLERY_CLASSES = frozenset({"hotfix", "forms"})

_LOCK = Lock()
# episode_id → PrefetchEpisode
_STORE: dict[str, "PrefetchEpisode"] = {}
# session_id → episode_id
_SESSION_INDEX: dict[str, str] = {}


def prefetch_enabled() -> bool:
	raw = (os.environ.get("PERCEPTION_EPISODE_PREFETCH") or "1").strip().lower()
	return raw not in {"0", "false", "off", "no"}


def hard_budget_s() -> float:
	try:
		return max(1.0, float(os.environ.get("PERCEPTION_PREFETCH_HARD_S") or _HARD_BUDGET_S))
	except ValueError:
		return _HARD_BUDGET_S


@dataclass
class FamilyResult:
	family: str
	status: str = "pending"  # pending | ready | error | skipped | cancelled | timeout
	started_at: float = 0.0
	finished_at: float = 0.0
	payload: dict[str, Any] = field(default_factory=dict)
	error: str | None = None

	def to_dict(self) -> dict[str, Any]:
		out: dict[str, Any] = {
			"family": self.family,
			"status": self.status,
			"latency_ms": int(max(0.0, (self.finished_at - self.started_at) * 1000))
			if self.finished_at and self.started_at
			else None,
		}
		if self.error:
			out["error"] = self.error
		# Surface only agent-safe keys (no giant payloads on the card).
		for key in (
			"discover_token",
			"candidate_count",
			"query",
			"providers",
			"shortlist_count",
			"asset_count",
			"tool",
		):
			if key in self.payload:
				out[key] = self.payload[key]
		return out


@dataclass
class PrefetchEpisode:
	episode_id: str
	session_id: str | None
	query: str
	face_class: str
	evidence_band: str
	families: list[str] = field(default_factory=list)
	status: str = "idle"  # idle | running | ready | partial | cancelled | skipped
	results: dict[str, FamilyResult] = field(default_factory=dict)
	tasks: list[asyncio.Task[Any]] = field(default_factory=list)
	started_at: float = 0.0
	finished_at: float = 0.0

	def snapshot(self) -> dict[str, Any]:
		ready = [
			f
			for f, r in self.results.items()
			if r.status == "ready"
		]
		pending = [
			f
			for f, r in self.results.items()
			if r.status == "pending"
		]
		# Non-browser families the host MAY call in parallel (policy hint only).
		can_parallel = [
			f
			for f in ready
			if f in {"inspiration", "component", "creative_kit", "resources"}
		]
		# Alias creative_kit → resources for face-card parallel batch.
		if "creative_kit" in can_parallel and "resources" not in can_parallel:
			can_parallel.append("resources")
		return {
			"status": self.status,
			"episode_id": self.episode_id,
			"query": self.query,
			"families": list(self.families),
			"ready": ready,
			"pending": pending,
			"prefetch_ready": bool(ready) and not pending and self.status in {"ready", "partial"},
			"can_parallel": can_parallel,
			"results": {k: v.to_dict() for k, v in self.results.items()},
			"hard_budget_s": hard_budget_s(),
			"browser_parallel": False,
		}


def families_for_prefetch(
	*,
	face_class: str,
	evidence_band: str,
	pack_remaining: list[str] | None = None,
) -> list[str]:
	"""Decide which HTTP families to warm. Empty for light/hotfix."""
	if not prefetch_enabled():
		return []
	cls = str(face_class or "").strip().lower()
	band = str(evidence_band or "").strip().lower()
	if cls in _NO_GALLERY_CLASSES:
		return []
	if band not in _HEAVY_BANDS:
		# Medium design classes: warm creative kit + inspiration scout only.
		if band == "medium" and cls in _MEDIUM_WARM_CLASSES:
			return ["creative_kit", "inspiration"]
		return []
	remaining = {str(x).rstrip("?").strip() for x in (pack_remaining or []) if x}
	# Session_start may not have portfolio unpaid yet — fall back to class pack.
	if not remaining and cls in {"greenfield", "redesign", "feature", "mockup"}:
		if cls in {"greenfield", "mockup"}:
			remaining = {"inspiration", "component", "visual_feedback", "observe", "verify"}
		elif cls == "redesign":
			remaining = {"observe", "snapshot", "visual_feedback", "component", "verify"}
		elif cls == "feature":
			remaining = {"observe", "component", "visual_feedback", "verify"}
	out: list[str] = []
	if "inspiration" in remaining:
		out.append("inspiration")
	if "component" in remaining:
		out.append("component")
	# Creative kit is advisory attach — not pack-critical.
	if cls in _CREATIVE_CLASSES or cls == "mockup" or "resources" in remaining:
		out.append("creative_kit")
	return out


def get_prefetch_snapshot(episode_id: str | None) -> dict[str, Any] | None:
	eid = str(episode_id or "").strip()
	if not eid:
		return None
	with _LOCK:
		row = _STORE.get(eid)
		if row is None:
			return None
		return row.snapshot()


def get_prefetch_snapshot_for_session(session_id: str | None) -> dict[str, Any] | None:
	sid = str(session_id or "").strip()
	if not sid:
		return None
	with _LOCK:
		eid = _SESSION_INDEX.get(sid)
		if not eid:
			return None
		row = _STORE.get(eid)
		if row is None:
			return None
		return row.snapshot()


def peek_inspiration_prefetch(
	*,
	episode_id: str | None = None,
	session_id: str | None = None,
	query: str | None = None,
) -> dict[str, Any] | None:
	"""Return discover_token payload when prefetch matches query."""
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return None
	fam = row.results.get("inspiration")
	if fam is None or fam.status != "ready":
		return None
	payload = fam.payload
	q = str(query or "").strip().lower()
	cached_q = str(payload.get("query") or "").strip().lower()
	if q and cached_q and q != cached_q and q not in cached_q and cached_q not in q:
		return None
	token = payload.get("discover_token")
	if not token:
		return None
	return {
		"discover_token": token,
		"query": payload.get("query"),
		"candidate_count": payload.get("candidate_count"),
		"candidates": list(payload.get("candidates") or []),
		"providers": list(payload.get("providers") or []),
		"source": "episode_prefetch",
	}


def peek_creative_kit(
	*,
	episode_id: str | None = None,
	session_id: str | None = None,
) -> dict[str, Any] | None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return None
	fam = row.results.get("creative_kit")
	if fam is None or fam.status != "ready":
		return None
	return dict(fam.payload)


def peek_component_shortlist(
	*,
	episode_id: str | None = None,
	session_id: str | None = None,
) -> dict[str, Any] | None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return None
	fam = row.results.get("component")
	if fam is None or fam.status != "ready":
		return None
	return dict(fam.payload)


def cancel_episode_prefetch(episode_id: str | None = None, *, session_id: str | None = None) -> None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return
	for task in list(row.tasks):
		if not task.done():
			task.cancel()
	row.status = "cancelled"
	row.finished_at = time.time()
	for fam in row.results.values():
		if fam.status == "pending":
			fam.status = "cancelled"
			fam.finished_at = time.time()
	with _LOCK:
		_STORE.pop(row.episode_id, None)
		if row.session_id:
			_SESSION_INDEX.pop(row.session_id, None)


def schedule_episode_prefetch(
	*,
	episode_id: str,
	session_id: str | None,
	query: str,
	face_class: str,
	evidence_band: str,
	pack_remaining: list[str] | None = None,
	repo_root: str = "",
	project_id: str = "default",
) -> dict[str, Any] | None:
	"""Fire-and-forget HTTP prefetch. Returns initial snapshot or None if skipped."""
	if not prefetch_enabled():
		return None
	eid = str(episode_id or "").strip()
	if not eid:
		return None
	q = str(query or "").strip()
	families = families_for_prefetch(
		face_class=face_class,
		evidence_band=evidence_band,
		pack_remaining=pack_remaining,
	)
	if not families or not q:
		return None

	try:
		loop = asyncio.get_running_loop()
	except RuntimeError:
		logger.debug("episode_prefetch: no running loop; skip")
		return None

	row = PrefetchEpisode(
		episode_id=eid,
		session_id=session_id,
		query=q,
		face_class=str(face_class or ""),
		evidence_band=str(evidence_band or ""),
		families=list(families),
		status="running",
		started_at=time.time(),
	)
	for fam in families:
		row.results[fam] = FamilyResult(family=fam, status="pending", started_at=time.time())

	with _LOCK:
		# Cancel prior for same episode.
		prior = _STORE.get(eid)
		if prior is not None:
			for task in list(prior.tasks):
				if not task.done():
					task.cancel()
		_STORE[eid] = row
		if session_id:
			_SESSION_INDEX[str(session_id)] = eid

	task = loop.create_task(
		_run_prefetch(
			row,
			repo_root=repo_root,
			project_id=project_id,
		),
		name=f"episode_prefetch:{eid}",
	)
	row.tasks.append(task)
	return row.snapshot()


async def _run_prefetch(
	row: PrefetchEpisode,
	*,
	repo_root: str,
	project_id: str,
) -> None:
	budget = hard_budget_s()
	coros = []
	for fam in row.families:
		coros.append(
			_run_family(
				row,
				fam,
				repo_root=repo_root,
				project_id=project_id,
				budget=budget,
			)
		)
	if coros:
		await asyncio.gather(*coros, return_exceptions=True)
	ready = sum(1 for r in row.results.values() if r.status == "ready")
	failed = sum(1 for r in row.results.values() if r.status in {"error", "timeout", "cancelled"})
	row.finished_at = time.time()
	if ready and failed == 0 and all(r.status == "ready" for r in row.results.values()):
		row.status = "ready"
	elif ready:
		row.status = "partial"
	elif row.status != "cancelled":
		row.status = "ready" if ready else "partial"


async def _run_family(
	row: PrefetchEpisode,
	family: str,
	*,
	repo_root: str,
	project_id: str,
	budget: float,
) -> None:
	fam = row.results[family]
	fam.started_at = time.time()
	try:
		if family == "inspiration":
			payload = await asyncio.wait_for(
				_prefetch_inspiration(row.query, repo_root=repo_root, project_id=project_id),
				timeout=budget,
			)
		elif family == "component":
			payload = await asyncio.wait_for(
				_prefetch_component(row.query),
				timeout=budget,
			)
		elif family == "creative_kit":
			payload = await asyncio.wait_for(
				_prefetch_creative_kit(row.query, repo_root=repo_root, project_id=project_id),
				timeout=budget,
			)
		else:
			fam.status = "skipped"
			fam.finished_at = time.time()
			return
		fam.payload = payload
		fam.status = "ready"
	except asyncio.TimeoutError:
		fam.status = "timeout"
		fam.error = f"prefetch_timeout_{budget}s"
		logger.info("episode_prefetch timeout family=%s episode=%s", family, row.episode_id)
	except asyncio.CancelledError:
		fam.status = "cancelled"
		fam.error = "cancelled"
		raise
	except Exception as exc:  # noqa: BLE001 — prefetch must never break session_start
		fam.status = "error"
		fam.error = str(exc)[:240]
		logger.info("episode_prefetch error family=%s: %s", family, exc)
	finally:
		fam.finished_at = time.time()


async def _prefetch_inspiration(
	query: str,
	*,
	repo_root: str,
	project_id: str,
) -> dict[str, Any]:
	from navigation.inspiration_intelligence import (
		InspirationDiscoveryRequest,
		InspirationIntelligenceService,
	)
	from navigation.inspiration_intelligence.scout_cache import mint_discover_token

	service = InspirationIntelligenceService()
	result = await service.discover(
		InspirationDiscoveryRequest(
			query=query,
			max_candidates=8,
			repo_root=repo_root,
			project_id=project_id,
		)
	)
	scout_rows: list[dict[str, Any]] = []
	for ranked in result.candidates:
		cand = ranked.candidate
		scout_rows.append(
			{
				"candidate_id": cand.candidate_id,
				"title": cand.title,
				"url": cand.url,
				"preview_url": cand.preview_ref,
				"preview_ref": cand.preview_ref,
				"provider_id": cand.provider_id,
				"external_id": cand.external_id,
				"discovery_score": float(
					getattr(ranked, "overall_score", None) or cand.discovery_score or 0
				),
				"source_kind": "gallery_image",
			}
		)
	token = mint_discover_token(
		query=query,
		candidates=scout_rows,
		provider_ids=list(result.search_plan.provider_ids),
	)
	return {
		"discover_token": token,
		"query": query,
		"candidate_count": len(scout_rows),
		"candidates": scout_rows[:8],
		"providers": list(result.search_plan.provider_ids),
		"tool": "perception_inspiration_collect",
		"degraded": list(result.degraded),
	}


async def _prefetch_component(query: str) -> dict[str, Any]:
	from navigation.component_intelligence.service import ComponentIntelligenceService

	service = ComponentIntelligenceService()
	# Prefer plan + light search — HTTP/catalog only; no browser.
	plan = service.build_search_plan(query)
	response = await service.search_components(query)
	shortlist: list[dict[str, Any]] = []
	for cand in list(response.candidates or [])[:8]:
		if hasattr(cand, "to_dict"):
			row = cand.to_dict()
		elif isinstance(cand, dict):
			row = cand
		else:
			row = {"name": getattr(cand, "name", None) or str(cand)}
		shortlist.append(row)
	return {
		"query": query,
		"shortlist_count": len(shortlist),
		"shortlist": shortlist,
		"plan": plan.to_dict() if hasattr(plan, "to_dict") else {},
		"tool": "perception_select_component_foundation",
		"degraded": list(getattr(response, "degraded", None) or []),
	}


async def _prefetch_creative_kit(
	query: str,
	*,
	repo_root: str,
	project_id: str,
) -> dict[str, Any]:
	"""Warm a multi-category creative kit (fonts, patterns, gradients, graphics, motion).

	Not pack-critical — advisory attach so agents use Resource Intelligence for
	core atmosphere assets instead of inventing flat CSS-only chrome.
	"""
	import asyncio

	from navigation.resource_intelligence import ResourceIntelligenceService
	from navigation.resource_intelligence.models import ResourceCategory, ResourceDiscoveryRequest

	categories = _creative_kit_categories(query)
	service = ResourceIntelligenceService()

	async def _one(cat: ResourceCategory, q: str) -> dict[str, Any]:
		try:
			result = await service.search(
				ResourceDiscoveryRequest(
					query=q,
					categories=[cat],
					max_results=4,
					repo_root=repo_root,
					project_id=project_id,
				)
			)
			assets = [a.to_dict() for a in (result.assets or [])[:4]]
			return {
				"category": cat.value,
				"query": q,
				"asset_count": len(assets),
				"assets": assets,
				"selection": result.selection.to_dict() if result.selection else None,
				"degraded": list(result.degraded or []),
			}
		except Exception as exc:  # noqa: BLE001
			return {
				"category": cat.value,
				"query": q,
				"asset_count": 0,
				"assets": [],
				"error": str(exc)[:160],
			}

	jobs = [
		_one(cat, _kit_query_for_category(query, cat))
		for cat in categories
	]
	bundles = list(await asyncio.gather(*jobs)) if jobs else []
	flat: list[dict[str, Any]] = []
	for bundle in bundles:
		for asset in bundle.get("assets") or []:
			if isinstance(asset, dict):
				row = dict(asset)
				row.setdefault("kit_category", bundle.get("category"))
				flat.append(row)
	return {
		"query": query,
		"categories": [c.value for c in categories],
		"bundles": bundles,
		"asset_count": len(flat),
		"assets": flat[:16],
		"tool": "perception_creative_assets",
		"gateway": "perception_creative_assets",
		"suggested_calls": [
			{
				"tool": "perception_creative_assets",
				"args": {
					"query": _kit_query_for_category(query, cat),
					"categories": [cat.value],
				},
			}
			for cat in categories
		],
		"degraded": [
			d
			for b in bundles
			for d in (b.get("degraded") or [])
		],
	}


def _creative_kit_categories(query: str) -> list[Any]:
	from navigation.resource_intelligence.models import ResourceCategory

	text = str(query or "").lower()
	# Core atmosphere set for structural UI — always warm these.
	core = [
		ResourceCategory.FONT,
		ResourceCategory.PATTERN,
		ResourceCategory.GRADIENT,
		ResourceCategory.ICON,
	]
	extra: list[Any] = []
	if re_search_any(
		text,
		(
			r"\b(animat|motion|lottie|micro[-\s]?interact)",
			r"\b(loading|spinner|confetti)\b",
		),
	):
		extra.append(ResourceCategory.ANIMATION)
	if re_search_any(
		text,
		(
			r"\b(illustrat|graphic|doodle|hero art|empty state)\b",
			r"\b(svg scene|spot illustration)\b",
		),
	):
		extra.append(ResourceCategory.ILLUSTRATION)
	if re_search_any(text, (r"\b(photo|photography|stock image|background image)\b",)):
		extra.append(ResourceCategory.PHOTO)
	if re_search_any(text, (r"\b(avatar|user (pic|photo)|profile image)\b",)):
		extra.append(ResourceCategory.AVATAR)
	# Landing / redesign / brand work → include illustration + light animation.
	if re_search_any(
		text,
		(
			r"\b(landing|greenfield|brand|marketing|hero|redesign|from scratch)\b",
			r"\b(look|design|visual|atmosphere|footer|page)\b",
		),
	):
		if ResourceCategory.ILLUSTRATION not in extra:
			extra.append(ResourceCategory.ILLUSTRATION)
		if ResourceCategory.ANIMATION not in extra:
			extra.append(ResourceCategory.ANIMATION)
	seen: set[str] = set()
	out: list[Any] = []
	for cat in [*core, *extra]:
		key = cat.value
		if key in seen:
			continue
		seen.add(key)
		out.append(cat)
	return out[:6]


def _kit_query_for_category(seed: str, category: Any) -> str:
	base = str(seed or "ui").strip()[:80]
	label = getattr(category, "value", str(category))
	suffix = {
		"font": "display font pairing",
		"pattern": "subtle background pattern texture",
		"gradient": "background gradient color palette",
		"icon": "ui icon set",
		"illustration": "hero illustration graphic",
		"animation": "ui micro animation lottie",
		"photo": "atmospheric background photo",
		"avatar": "user avatar",
	}.get(label, label)
	return f"{base} {suffix}".strip()


def re_search_any(text: str, patterns: tuple[str, ...]) -> bool:
	import re

	return any(re.search(p, text) for p in patterns)


def _resolve_row(
	*,
	episode_id: str | None,
	session_id: str | None,
) -> PrefetchEpisode | None:
	with _LOCK:
		eid = str(episode_id or "").strip()
		if not eid and session_id:
			eid = _SESSION_INDEX.get(str(session_id).strip()) or ""
		if not eid:
			return None
		return _STORE.get(eid)


def clear_prefetch_store() -> None:
	"""Test helper."""
	with _LOCK:
		for row in list(_STORE.values()):
			for task in list(row.tasks):
				if not task.done():
					task.cancel()
		_STORE.clear()
		_SESSION_INDEX.clear()


# Soft budget exported for docs/metrics.
SOFT_BUDGET_S = _SOFT_BUDGET_S
