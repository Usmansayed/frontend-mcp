"""Continuous parallel inspiration pulse — HTTP-only background scout.

Keeps warming visual refs from the internet for the whole episode so hosts
can LOOK many images without waiting on one-shot collect.

Invariants:
- Never touches the primary app browser / SessionStore.
- Parallel HTTP discover + CDN/OG thumb materialize only.
- Starts at session_start (design classes); cancels on session_end.
- Pauses after inspiration look_lock / direction_locked (dev64 digest gate).
- Results surface on card.inspiration_pulse + peek helpers for tools.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_S = 10.0
_DEFAULT_WAVE_HARD_S = 12.0
_DEFAULT_MAX_THUMBS = 24
_DEFAULT_WAVE_CANDIDATES = 8
_DESIGN_CLASSES = frozenset({"greenfield", "redesign", "mockup"})
_NO_PULSE_CLASSES = frozenset({"hotfix", "forms"})

_LOCK = Lock()
_STORE: dict[str, "InspirationPulseEpisode"] = {}
_SESSION_INDEX: dict[str, str] = {}


def pulse_enabled() -> bool:
	raw = (os.environ.get("PERCEPTION_INSPIRATION_PULSE") or "1").strip().lower()
	return raw not in {"0", "false", "off", "no"}


def pulse_interval_s() -> float:
	try:
		return max(3.0, float(os.environ.get("PERCEPTION_INSPIRATION_PULSE_INTERVAL_S") or _DEFAULT_INTERVAL_S))
	except ValueError:
		return _DEFAULT_INTERVAL_S


def pulse_wave_hard_s() -> float:
	try:
		return max(3.0, float(os.environ.get("PERCEPTION_INSPIRATION_PULSE_HARD_S") or _DEFAULT_WAVE_HARD_S))
	except ValueError:
		return _DEFAULT_WAVE_HARD_S


def pulse_max_thumbs() -> int:
	try:
		return max(4, min(48, int(os.environ.get("PERCEPTION_INSPIRATION_PULSE_MAX_THUMBS") or _DEFAULT_MAX_THUMBS)))
	except ValueError:
		return _DEFAULT_MAX_THUMBS


def pulse_after_lock() -> bool:
	"""If false (default), pause pulsing once direction is look-locked."""
	raw = (os.environ.get("PERCEPTION_INSPIRATION_PULSE_AFTER_LOCK") or "0").strip().lower()
	return raw in {"1", "true", "on", "yes"}


def should_start_pulse(*, face_class: str, evidence_band: str) -> bool:
	if not pulse_enabled():
		return False
	cls = str(face_class or "").strip().lower()
	band = str(evidence_band or "").strip().lower()
	if cls in _NO_PULSE_CLASSES:
		return False
	if cls in _DESIGN_CLASSES:
		return band in {"medium", "heavy", "very_heavy"} or not band
	# Feature additive: allow heavy+ only
	if cls == "feature":
		return band in {"heavy", "very_heavy"}
	return False


@dataclass
class Thumb:
	ref_id: str
	title: str
	url: str
	preview_url: str
	blob_path: str | None
	provider_id: str
	generation: int
	added_at: float

	def to_dict(self) -> dict[str, Any]:
		out: dict[str, Any] = {
			"ref_id": self.ref_id,
			"title": self.title,
			"url": self.url,
			"preview_url": self.preview_url,
			"provider_id": self.provider_id,
			"generation": self.generation,
		}
		if self.blob_path:
			out["blob_path"] = self.blob_path
			out["inspiration_blob"] = self.blob_path
		return out


@dataclass
class InspirationPulseEpisode:
	episode_id: str
	session_id: str | None
	query: str
	face_class: str
	evidence_band: str
	status: str = "idle"  # idle|running|paused|cancelled|skipped
	generation: int = 0
	thumbs: list[Thumb] = field(default_factory=list)
	seen_urls: set[str] = field(default_factory=set)
	seen_ids: set[str] = field(default_factory=set)
	discover_token: str | None = None
	blob_session_id: str | None = None
	look_locked: bool = False
	last_error: str | None = None
	started_at: float = 0.0
	last_wave_at: float = 0.0
	task: asyncio.Task[Any] | None = None
	repo_root: str = ""
	project_id: str = "default"

	def snapshot(self) -> dict[str, Any]:
		max_show = min(12, pulse_max_thumbs())
		thumbs = [t.to_dict() for t in self.thumbs[-max_show:]]
		thumbs.reverse()  # newest first for agents
		return {
			"status": self.status,
			"episode_id": self.episode_id,
			"query": self.query,
			"generation": self.generation,
			"thumb_count": len(self.thumbs),
			"thumbs": thumbs,
			"discover_token": self.discover_token,
			"blob_session_id": self.blob_session_id,
			"look_locked": self.look_locked,
			"interval_s": pulse_interval_s(),
			"browser_parallel": False,
			"http_parallel": True,
			"last_error": self.last_error,
			"tool": "perception_inspiration_pulse",
			"note": (
				"Background HTTP inspiration pulse — LOOK thumbs, then "
				"perception_visual_feedback purpose=inspiration with primary_ref_ids + borrow."
				if self.status in {"running", "paused"}
				else None
			),
		}


def get_pulse_snapshot(episode_id: str | None) -> dict[str, Any] | None:
	eid = str(episode_id or "").strip()
	if not eid:
		return None
	with _LOCK:
		row = _STORE.get(eid)
		return row.snapshot() if row else None


def get_pulse_snapshot_for_session(session_id: str | None) -> dict[str, Any] | None:
	sid = str(session_id or "").strip()
	if not sid:
		return None
	with _LOCK:
		eid = _SESSION_INDEX.get(sid)
		if not eid:
			return None
		row = _STORE.get(eid)
		return row.snapshot() if row else None


def peek_pulse_discover_token(
	*,
	episode_id: str | None = None,
	session_id: str | None = None,
	query: str | None = None,
) -> dict[str, Any] | None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None or not row.discover_token:
		return None
	q = str(query or "").strip().lower()
	cached_q = str(row.query or "").strip().lower()
	if q and cached_q and q != cached_q and q not in cached_q and cached_q not in q:
		return None
	return {
		"discover_token": row.discover_token,
		"query": row.query,
		"candidate_count": len(row.thumbs),
		"candidates": [t.to_dict() for t in row.thumbs[-12:]],
		"blob_session_id": row.blob_session_id,
		"generation": row.generation,
		"source": "inspiration_pulse",
	}


def mark_pulse_look_locked(
	*,
	episode_id: str | None = None,
	session_id: str | None = None,
	locked: bool = True,
) -> None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return
	row.look_locked = bool(locked)
	if row.look_locked and not pulse_after_lock() and row.status == "running":
		row.status = "paused"


def clear_pulse_store() -> None:
	with _LOCK:
		for row in list(_STORE.values()):
			if row.task and not row.task.done():
				row.task.cancel()
		_STORE.clear()
		_SESSION_INDEX.clear()


def cancel_inspiration_pulse(
	episode_id: str | None = None,
	*,
	session_id: str | None = None,
) -> None:
	row = _resolve_row(episode_id=episode_id, session_id=session_id)
	if row is None:
		return
	row.status = "cancelled"
	if row.task and not row.task.done():
		row.task.cancel()
	with _LOCK:
		_STORE.pop(row.episode_id, None)
		if row.session_id:
			_SESSION_INDEX.pop(row.session_id, None)


def schedule_inspiration_pulse(
	*,
	episode_id: str,
	session_id: str | None,
	query: str,
	face_class: str,
	evidence_band: str,
	repo_root: str = "",
	project_id: str = "default",
) -> dict[str, Any] | None:
	"""Start continuous HTTP pulse. Returns snapshot or None if skipped."""
	if not should_start_pulse(face_class=face_class, evidence_band=evidence_band):
		return None
	eid = str(episode_id or "").strip()
	q = str(query or "").strip()
	if not eid or not q:
		return None
	try:
		loop = asyncio.get_running_loop()
	except RuntimeError:
		logger.debug("inspiration_pulse: no running loop; skip")
		return None

	row = InspirationPulseEpisode(
		episode_id=eid,
		session_id=session_id,
		query=q,
		face_class=str(face_class or ""),
		evidence_band=str(evidence_band or ""),
		status="running",
		started_at=time.time(),
		repo_root=repo_root,
		project_id=project_id,
	)
	with _LOCK:
		prior = _STORE.get(eid)
		if prior is not None and prior.task and not prior.task.done():
			prior.status = "cancelled"
			prior.task.cancel()
		_STORE[eid] = row
		if session_id:
			_SESSION_INDEX[str(session_id)] = eid

	task = loop.create_task(_run_pulse_loop(row), name=f"inspiration_pulse:{eid}")
	row.task = task
	return row.snapshot()


def _resolve_row(
	*,
	episode_id: str | None,
	session_id: str | None,
) -> InspirationPulseEpisode | None:
	with _LOCK:
		eid = str(episode_id or "").strip()
		if eid and eid in _STORE:
			return _STORE[eid]
		sid = str(session_id or "").strip()
		if sid:
			mapped = _SESSION_INDEX.get(sid)
			if mapped:
				return _STORE.get(mapped)
	return None


async def _run_pulse_loop(row: InspirationPulseEpisode) -> None:
	"""Wave → sleep → wave until cancelled / paused-after-lock."""
	# First wave immediately (don't wait interval).
	while row.status not in {"cancelled"}:
		if row.look_locked and not pulse_after_lock():
			row.status = "paused"
			return
		try:
			await asyncio.wait_for(_run_one_wave(row), timeout=pulse_wave_hard_s())
		except asyncio.TimeoutError:
			row.last_error = "wave_timeout"
			logger.debug("inspiration_pulse wave timeout episode=%s", row.episode_id)
		except asyncio.CancelledError:
			row.status = "cancelled"
			raise
		except Exception as exc:
			row.last_error = str(exc)[:200]
			logger.debug("inspiration_pulse wave error: %s", exc)
		if row.status == "cancelled":
			return
		if row.look_locked and not pulse_after_lock():
			row.status = "paused"
			return
		try:
			await asyncio.sleep(pulse_interval_s())
		except asyncio.CancelledError:
			row.status = "cancelled"
			raise


async def _run_one_wave(row: InspirationPulseEpisode) -> None:
	from navigation.inspiration_intelligence import (
		InspirationDiscoveryRequest,
		InspirationIntelligenceService,
	)
	from navigation.inspiration_intelligence.scout_cache import mint_discover_token
	from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

	service = InspirationIntelligenceService()
	# Rotate query slightly by generation to diversify providers.
	query = row.query
	if row.generation > 0 and row.generation % 2 == 1:
		query = f"{row.query} UI chrome layout"
	elif row.generation > 0 and row.generation % 3 == 2:
		query = f"{row.query} dark elegant workspace"

	result = await service.discover(
		InspirationDiscoveryRequest(
			query=query,
			max_candidates=_DEFAULT_WAVE_CANDIDATES,
			repo_root=row.repo_root,
			project_id=row.project_id,
		)
	)
	scout_rows: list[dict[str, Any]] = []
	new_hits: list[dict[str, Any]] = []
	for ranked in result.candidates:
		cand = ranked.candidate
		url = str(cand.url or "").strip()
		cid = str(cand.candidate_id or "").strip()
		preview = str(cand.preview_ref or "").strip()
		if not url and not preview:
			continue
		norm = _norm_url(url or preview)
		if norm in row.seen_urls or (cid and cid in row.seen_ids):
			continue
		row_dict = {
			"candidate_id": cid or f"pulse:{row.generation}:{len(new_hits)}",
			"title": cand.title,
			"url": url,
			"preview_url": preview,
			"preview_ref": preview,
			"provider_id": cand.provider_id,
			"external_id": cand.external_id,
			"discovery_score": float(
				getattr(ranked, "overall_score", None) or cand.discovery_score or 0
			),
			"source_kind": "gallery_image",
		}
		new_hits.append(row_dict)
		scout_rows.append(row_dict)

	# Include prior thumbs in token so collect can reuse full ring.
	for t in row.thumbs[-12:]:
		scout_rows.append(
			{
				"candidate_id": t.ref_id,
				"title": t.title,
				"url": t.url,
				"preview_url": t.preview_url,
				"preview_ref": t.preview_url,
				"provider_id": t.provider_id,
				"source_kind": "gallery_image",
			}
		)

	token = mint_discover_token(
		query=row.query,
		candidates=scout_rows[:24],
		provider_ids=list(result.search_plan.provider_ids),
	)
	row.discover_token = token
	row.generation += 1
	row.last_wave_at = time.time()

	store = InspirationBlobStore()
	if not row.blob_session_id:
		row.blob_session_id = store.create_session(purpose=f"pulse:{row.query[:80]}")
	# Materialize only new hits (HTTP/CDN) — parallel inside store when available.
	materialize = getattr(store, "materialize_hits_async", None)
	if callable(materialize) and new_hits:
		try:
			await materialize(row.blob_session_id, new_hits, concurrency=5)
		except Exception:
			store.materialize_hits(row.blob_session_id, new_hits)
	elif new_hits:
		store.materialize_hits(row.blob_session_id, new_hits)

	for hit in new_hits:
		cid = str(hit.get("candidate_id") or "")
		url = str(hit.get("url") or "")
		preview = str(hit.get("preview_url") or hit.get("preview_ref") or "")
		blob = str(hit.get("inspiration_blob") or "").strip() or None
		row.seen_urls.add(_norm_url(url or preview))
		if cid:
			row.seen_ids.add(cid)
		row.thumbs.append(
			Thumb(
				ref_id=cid,
				title=str(hit.get("title") or "")[:120],
				url=url,
				preview_url=preview,
				blob_path=blob,
				provider_id=str(hit.get("provider_id") or ""),
				generation=row.generation,
				added_at=time.time(),
			)
		)
	# Cap ring buffer
	max_thumbs = pulse_max_thumbs()
	if len(row.thumbs) > max_thumbs:
		row.thumbs = row.thumbs[-max_thumbs:]
	row.last_error = None
	if row.status != "cancelled":
		row.status = "running"


def _norm_url(url: str) -> str:
	raw = str(url or "").strip().lower()
	if not raw:
		return ""
	try:
		parsed = urlparse(raw)
		return f"{parsed.netloc}{parsed.path}".rstrip("/")
	except Exception:
		return raw
