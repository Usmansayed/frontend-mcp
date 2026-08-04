"""Primary-browser single-flight lock — P4 enforce.

One Chromium per MCP process (BrowserSessionManager). Parallel MCP browser
tools on the same process race navigation/observe. This module serializes
browser-bound tools with a queue + wait timeout.

Non-browser tools (resources, discover, resolve_*, components) never take
this lock — they stay parallel-safe with episode prefetch.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

_DEFAULT_WAIT_S = 60.0

# Tools that touch the shared primary browser (or session-bound page state).
BROWSER_FLIGHT_TOOLS: frozenset[str] = frozenset(
	{
		"perception_session_start",
		"perception_session_end",
		"perception_navigate",
		"perception_navigate_and_observe",
		"perception_observe",
		"perception_execute_script",
		"perception_execute_actions",
		"perception_verify",
		"perception_diff",
		"perception_auth_gate",
		"perception_probe_form",
		"perception_probe_guards",
		"perception_state_save",
		"perception_state_restore",
		"perception_flow_describe",
		"perception_console_get",
		"perception_console_clear",
		"perception_network_get",
		"perception_network_clear",
		"perception_visual_feedback",
		"perception_build_design_snapshot",
		"perception_design_review",
		"perception_resource_observe_bridge",
		"perception_correlate_live",
		"perception_audit_accessibility",
		"perception_audit_performance",
		"perception_audit_seo",
		"perception_audit_best_practices",
		"perception_full_diagnosis",
		"perception_debug_mode",
		"perception_audit_mode",
		# May navigate the shared browser for screenshots / live capture.
		"perception_inspiration_collect",
		# pulse is HTTP-only continuous/read — do not serialize on primary browser
		"perception_inspiration_widen",
	}
)


@dataclass
class BrowserFlightHold:
	tool: str
	session_id: str | None
	wait_ms: int
	acquired_at: float


@dataclass
class _FlightState:
	lock: asyncio.Lock | None = None
	loop_id: int | None = None
	holder_tool: str | None = None
	holder_session_id: str | None = None
	acquired_at: float = 0.0
	waiters: int = 0


_STATE = _FlightState()


def _lock() -> asyncio.Lock:
	"""Lazy lock bound to the current event loop (pytest creates fresh loops)."""
	loop = asyncio.get_running_loop()
	loop_id = id(loop)
	if _STATE.lock is None or _STATE.loop_id != loop_id:
		_STATE.lock = asyncio.Lock()
		_STATE.loop_id = loop_id
		_STATE.holder_tool = None
		_STATE.holder_session_id = None
		_STATE.acquired_at = 0.0
		_STATE.waiters = 0
	return _STATE.lock


class BrowserFlightTimeout(Exception):
	"""Timed out waiting for the primary browser flight lock."""

	def __init__(
		self,
		*,
		tool: str,
		session_id: str | None,
		wait_s: float,
		holder_tool: str | None,
	) -> None:
		self.tool = tool
		self.session_id = session_id
		self.wait_s = wait_s
		self.holder_tool = holder_tool
		super().__init__(
			f"browser_session_busy: waited {wait_s:.0f}s for primary browser "
			f"(holder={holder_tool or 'unknown'}); retry after current tool finishes"
		)


class BrowserFlightRejected(Exception):
	"""Reject mode: browser already in flight."""

	def __init__(self, *, tool: str, holder_tool: str | None) -> None:
		self.tool = tool
		self.holder_tool = holder_tool
		super().__init__(
			f"browser_session_busy: primary browser held by {holder_tool or 'another tool'}; "
			"call one browser tool at a time per session"
		)


def browser_lock_enabled() -> bool:
	raw = (os.environ.get("PERCEPTION_BROWSER_LOCK") or "1").strip().lower()
	return raw not in {"0", "false", "off", "no"}


def browser_lock_mode() -> str:
	"""queue (default) | reject."""
	raw = (os.environ.get("PERCEPTION_BROWSER_LOCK_MODE") or "queue").strip().lower()
	if raw in {"reject", "fail", "busy"}:
		return "reject"
	return "queue"


def browser_lock_wait_s() -> float:
	try:
		return max(0.05, float(os.environ.get("PERCEPTION_BROWSER_LOCK_WAIT_S") or _DEFAULT_WAIT_S))
	except ValueError:
		return _DEFAULT_WAIT_S


def requires_browser_flight(tool: str) -> bool:
	return str(tool or "") in BROWSER_FLIGHT_TOOLS


def flight_snapshot() -> dict[str, Any]:
	locked = bool(_STATE.lock and _STATE.lock.locked())
	return {
		"enabled": browser_lock_enabled(),
		"mode": browser_lock_mode(),
		"wait_s": browser_lock_wait_s(),
		"locked": locked,
		"holder_tool": _STATE.holder_tool,
		"holder_session_id": _STATE.holder_session_id,
		"waiters": _STATE.waiters,
	}


def reset_browser_flight_for_tests() -> None:
	"""Drop holder metadata; next acquire binds to the current loop."""
	_STATE.lock = None
	_STATE.loop_id = None
	_STATE.holder_tool = None
	_STATE.holder_session_id = None
	_STATE.acquired_at = 0.0
	_STATE.waiters = 0


@asynccontextmanager
async def browser_flight(
	*,
	tool: str,
	session_id: str | None = None,
) -> AsyncIterator[BrowserFlightHold | None]:
	"""Acquire primary-browser flight lock for browser-bound tools."""
	if not browser_lock_enabled() or not requires_browser_flight(tool):
		yield None
		return

	mode = browser_lock_mode()
	wait_s = browser_lock_wait_s()
	sid = str(session_id).strip() if session_id else None
	lock = _lock()

	if mode == "reject" and lock.locked():
		raise BrowserFlightRejected(tool=tool, holder_tool=_STATE.holder_tool)

	_STATE.waiters += 1
	wait_started = time.perf_counter()
	try:
		try:
			await asyncio.wait_for(lock.acquire(), timeout=wait_s)
		except asyncio.TimeoutError as exc:
			raise BrowserFlightTimeout(
				tool=tool,
				session_id=sid,
				wait_s=wait_s,
				holder_tool=_STATE.holder_tool,
			) from exc
	finally:
		_STATE.waiters = max(0, _STATE.waiters - 1)

	wait_ms = int((time.perf_counter() - wait_started) * 1000)
	_STATE.holder_tool = tool
	_STATE.holder_session_id = sid
	_STATE.acquired_at = time.time()
	hold = BrowserFlightHold(
		tool=tool,
		session_id=sid,
		wait_ms=wait_ms,
		acquired_at=_STATE.acquired_at,
	)
	if wait_ms > 50:
		logger.info(
			"browser_flight acquired tool=%s wait_ms=%s prior_holder_cleared",
			tool,
			wait_ms,
		)
	try:
		yield hold
	finally:
		_STATE.holder_tool = None
		_STATE.holder_session_id = None
		_STATE.acquired_at = 0.0
		lock.release()


def busy_envelope(
	tool: str,
	*,
	error: str,
	holder_tool: str | None = None,
	wait_s: float | None = None,
	session_id: str | None = None,
) -> dict[str, Any]:
	"""Structured busy response for hosts / agents."""
	retry_after = int((wait_s or browser_lock_wait_s()) * 1000)
	advisory = [
		"Call browser tools one at a time on the same session_id.",
		"Non-browser tools (creative_assets, inspiration_discover, resolve_*) do not need this lock.",
	]
	if holder_tool:
		advisory.insert(0, f"Primary browser currently held by {holder_tool}.")
	return {
		"contract_version": "1.0",
		"tool": tool,
		"ok": False,
		"error": error,
		"session_id": session_id,
		"degraded": ["browser_session_busy"],
		"data": {
			"browser_flight": {
				"busy": True,
				"holder_tool": holder_tool,
				"retry_after_ms": retry_after,
				"mode": browser_lock_mode(),
				**flight_snapshot(),
			},
			"agent_summary": {
				"blocking": ["browser_session_busy"],
				"advisory": advisory,
				"retry_after_ms": retry_after,
			},
		},
	}


def attach_flight_metadata(envelope: dict[str, Any], hold: BrowserFlightHold | None) -> None:
	if hold is None or not isinstance(envelope, dict):
		return
	data = envelope.setdefault("data", {})
	if not isinstance(data, dict):
		return
	meta = data.setdefault("browser_flight", {})
	if isinstance(meta, dict):
		meta["wait_ms"] = hold.wait_ms
		meta["held"] = True
		meta["tool"] = hold.tool
