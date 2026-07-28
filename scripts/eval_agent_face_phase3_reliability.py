"""Phase 3 — agent-face end-to-end reliability board.

Pass bar (coordination perfection design):
  - Class session boards finish with data.verified=true (no false-green)
  - inspiration / select return within bounded wall time (no hang)
  - Latency SLO met on BOARD classes
  - Short soak: sequential sessions do not crash the runtime

Usage:
  $env:PYTHONPATH="src"
  python -u scripts/eval_agent_face_phase3_reliability.py
  python -u scripts/eval_agent_face_phase3_reliability.py --url http://127.0.0.1:18765
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs/research/agent_face_phase3_reliability.json"
SLO_DOC = ROOT / "docs/research/coordination-perfection-phase3-slos.md"
DEFAULT_URL = "http://127.0.0.1:18765"

# Force fast inspiration path for reliability board (still must return bounded).
os.environ.setdefault("INSPIRATION_FORCE", "1")
os.environ.setdefault("INSPIRATION_FAST", "1")
os.environ.setdefault("INSPIRATION_HEADLESS", "true")
os.environ.setdefault("INSPIRATION_ALLOW_BROWSER_SCREENSHOT", "0")

# Wall-clock SLOs (ms) — local sandbox, headless browser.
SLO_MS: dict[str, int] = {
	"perception_health": 5_000,
	"perception_session_start": 20_000,
	"perception_navigate_and_observe": 25_000,
	"perception_probe_form": 20_000,
	"perception_verify": 20_000,
	"perception_inspiration_collect": 60_000,
	"perception_select_component_foundation": 15_000,
	"perception_visual_feedback": 15_000,
	"path_forms": 120_000,
	"path_hotfix": 90_000,
	"path_feature": 90_000,
	"path_greenfield_light": 180_000,
}


@dataclass
class Step:
	tool: str
	ok: bool
	latency_ms: int
	slo_ms: int
	slo_ok: bool
	verified: bool | None = None
	card_class: str | None = None
	error: str | None = None


@dataclass
class BoardRow:
	id: str
	ok: bool = False
	notes: list[str] = field(default_factory=list)
	steps: list[Step] = field(default_factory=list)
	wall_ms: int = 0
	error: str | None = None


def _card(env: dict[str, Any]) -> dict[str, Any]:
	summary = env.get("agent_summary") or {}
	card = summary.get("card")
	if isinstance(card, dict):
		return card
	inner = ((env.get("data") or {}).get("agent_summary") or {}).get("card")
	return inner if isinstance(inner, dict) else {}


async def _call(rt: Any, tool: str, args: dict[str, Any]) -> tuple[dict[str, Any], int]:
	t0 = time.perf_counter()
	result = await rt.execute_tool(tool, args, allow_repeat=True)
	ms = int((time.perf_counter() - t0) * 1000)
	env = result.envelope if hasattr(result, "envelope") else result
	if not isinstance(env, dict):
		env = {"ok": False, "error": "non-dict envelope"}
	return env, ms


def _step(tool: str, env: dict[str, Any], ms: int) -> Step:
	slo = SLO_MS.get(tool, 30_000)
	card = _card(env)
	verified = None
	if tool == "perception_verify":
		verified = bool((env.get("data") or {}).get("verified"))
	return Step(
		tool=tool,
		ok=bool(env.get("ok")),
		latency_ms=ms,
		slo_ms=slo,
		slo_ok=ms <= slo,
		verified=verified,
		card_class=card.get("class"),
		error=str(env.get("error") or "") or None,
	)


async def _end(rt: Any, sid: str | None) -> None:
	if not sid:
		return
	try:
		await asyncio.wait_for(
			rt.execute_tool("perception_session_end", {"session_id": sid}, allow_repeat=True),
			timeout=10.0,
		)
	except Exception:
		pass


async def board_forms(rt: Any, url: str) -> BoardRow:
	row = BoardRow(id="path_forms")
	t0 = time.perf_counter()
	sid = None
	try:
		intent = (
			"Verify the validation form at /forms/validation: "
			"invalid submit shows errors, valid submit shows success"
		)
		env, ms = await _call(rt, "perception_health", {"url": url, "intent": intent})
		row.steps.append(_step("perception_health", env, ms))
		if not env.get("ok") and not (env.get("data") or {}).get("reachable"):
			row.error = "sandbox unreachable"
			return row

		env, ms = await _call(
			rt,
			"perception_session_start",
			{"base_url": url, "intent": intent},
		)
		row.steps.append(_step("perception_session_start", env, ms))
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
		card = _card(env)
		if card.get("class") != "forms":
			row.notes.append(f"class={card.get('class')} want=forms")

		env, ms = await _call(
			rt,
			"perception_probe_form",
			{"session_id": sid, "url": "/forms/validation"},
		)
		row.steps.append(_step("perception_probe_form", env, ms))

		# invalid then valid — false-green trap if ok without verified
		env, ms = await _call(
			rt,
			"perception_verify",
			{
				"session_id": sid,
				"expectations": [
					{"kind": "text_absent", "value": "Form submitted successfully"},
				],
				"url": "/forms/validation",
			},
		)
		row.steps.append(_step("perception_verify", env, ms))
		# Trigger invalid path via probe already; now valid verify
		env, ms = await _call(
			rt,
			"perception_verify",
			{
				"session_id": sid,
				"expectations": [{"kind": "text", "value": "email"}],
				"url": "/forms/validation",
			},
		)
		row.steps.append(_step("perception_verify", env, ms))
		verified = bool((env.get("data") or {}).get("verified"))
		# False-green: transport ok but not verified when we require verified
		if env.get("ok") and not verified:
			row.notes.append("false_green: ok without data.verified")
		if not verified:
			row.notes.append("verified=false")

		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		path_slo = SLO_MS["path_forms"]
		slo_ok = row.wall_ms <= path_slo and all(s.slo_ok for s in row.steps)
		row.ok = verified and slo_ok and not any("false_green" in n for n in row.notes)
		if not slo_ok:
			row.notes.append(f"path_slo wall={row.wall_ms}>{path_slo} or tool SLO miss")
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		await _end(rt, str(sid) if sid else None)
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


async def board_hotfix(rt: Any, url: str) -> BoardRow:
	row = BoardRow(id="path_hotfix")
	t0 = time.perf_counter()
	sid = None
	try:
		intent = "Fix overlapping CTA button layout bug on the homepage — surgical CSS hotfix"
		env, ms = await _call(rt, "perception_health", {"url": url, "intent": intent})
		row.steps.append(_step("perception_health", env, ms))

		env, ms = await _call(
			rt, "perception_session_start", {"base_url": url, "intent": intent}
		)
		row.steps.append(_step("perception_session_start", env, ms))
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
		card = _card(env)
		if card.get("class") != "hotfix":
			row.notes.append(f"class={card.get('class')} want=hotfix")

		env, ms = await _call(
			rt,
			"perception_navigate_and_observe",
			{"session_id": sid, "url": "/", "include_screenshot": True},
		)
		row.steps.append(_step("perception_navigate_and_observe", env, ms))

		env, ms = await _call(
			rt,
			"perception_verify",
			{
				"session_id": sid,
				"expectations": [{"kind": "text", "value": "Home"}],
				"url": "/",
			},
		)
		row.steps.append(_step("perception_verify", env, ms))
		verified = bool((env.get("data") or {}).get("verified"))
		if env.get("ok") and not verified:
			row.notes.append("false_green: ok without data.verified")

		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		slo_ok = row.wall_ms <= SLO_MS["path_hotfix"] and all(s.slo_ok for s in row.steps)
		row.ok = verified and slo_ok and card.get("class") == "hotfix"
		if not slo_ok:
			row.notes.append(f"path_slo wall={row.wall_ms}")
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		await _end(rt, str(sid) if sid else None)
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


async def board_feature(rt: Any, url: str) -> BoardRow:
	row = BoardRow(id="path_feature")
	t0 = time.perf_counter()
	sid = None
	try:
		intent = "Add a settings toggle to an existing page — incremental feature"
		env, ms = await _call(rt, "perception_health", {"url": url, "intent": intent})
		row.steps.append(_step("perception_health", env, ms))

		env, ms = await _call(
			rt, "perception_session_start", {"base_url": url, "intent": intent}
		)
		row.steps.append(_step("perception_session_start", env, ms))
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
		card = _card(env)
		if card.get("class") != "feature":
			row.notes.append(f"class={card.get('class')} want=feature")

		env, ms = await _call(
			rt,
			"perception_navigate_and_observe",
			{"session_id": sid, "url": "/", "include_screenshot": True},
		)
		row.steps.append(_step("perception_navigate_and_observe", env, ms))
		# Class must not flip to hotfix after observe (host_action polish trap)
		post = _card(env)
		if post.get("class") != "feature":
			row.notes.append(f"post_observe_class={post.get('class')} want=feature")

		env, ms = await _call(
			rt,
			"perception_verify",
			{
				"session_id": sid,
				"expectations": [{"kind": "text", "value": "Home"}],
				"url": "/",
			},
		)
		row.steps.append(_step("perception_verify", env, ms))
		verified = bool((env.get("data") or {}).get("verified"))
		if env.get("ok") and not verified:
			row.notes.append("false_green: ok without data.verified")

		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		slo_ok = row.wall_ms <= SLO_MS["path_feature"] and all(s.slo_ok for s in row.steps)
		row.ok = (
			verified
			and slo_ok
			and card.get("class") == "feature"
			and post.get("class") == "feature"
		)
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		await _end(rt, str(sid) if sid else None)
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


async def board_inspiration_bounded(rt: Any, url: str) -> BoardRow:
	"""Inspiration must return (ok or degraded) within SLO — never hang the face."""
	row = BoardRow(id="inspiration_bounded")
	t0 = time.perf_counter()
	sid = None
	try:
		intent = "Build a new SaaS landing page with strong brand hero — greenfield design"
		env, ms = await _call(rt, "perception_health", {"url": url, "intent": intent})
		row.steps.append(_step("perception_health", env, ms))

		env, ms = await _call(
			rt, "perception_session_start", {"base_url": url, "intent": intent}
		)
		row.steps.append(_step("perception_session_start", env, ms))
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")

		# Hard wall: asyncio.wait_for slightly above SLO
		slo = SLO_MS["perception_inspiration_collect"]
		try:
			env, ms = await asyncio.wait_for(
				_call(
					rt,
					"perception_inspiration_collect",
					{
						"session_id": sid,
						"query": "saas landing brand hero",
						"inspiration_level": "light",
					},
				),
				timeout=(slo / 1000.0) + 5.0,
			)
		except asyncio.TimeoutError:
			row.error = f"inspiration hung >{slo + 5000}ms"
			row.ok = False
			return row
		row.steps.append(_step("perception_inspiration_collect", env, ms))
		# Must return — ok=false/degraded still counts as bounded if within SLO
		bounded = ms <= slo
		returned = True
		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		row.ok = bounded and returned
		if not bounded:
			row.notes.append(f"inspiration_slo ms={ms}>{slo}")
		if not env.get("ok"):
			row.notes.append(f"inspiration_ok=false err={env.get('error')}")
			# Still PASS if bounded (non-goal: provider perfection)
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		await _end(rt, str(sid) if sid else None)
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


async def board_select_bounded(rt: Any, url: str) -> BoardRow:
	row = BoardRow(id="select_bounded")
	t0 = time.perf_counter()
	sid = None
	try:
		intent = "Build a new SaaS landing page with strong brand hero — greenfield design"
		env, ms = await _call(
			rt, "perception_session_start", {"base_url": url, "intent": intent}
		)
		row.steps.append(_step("perception_session_start", env, ms))
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")

		slo = SLO_MS["perception_select_component_foundation"]
		try:
			env, ms = await asyncio.wait_for(
				_call(
					rt,
					"perception_select_component_foundation",
					{"session_id": sid, "query": "primary CTA button"},
				),
				timeout=(slo / 1000.0) + 5.0,
			)
		except asyncio.TimeoutError:
			row.error = f"select hung >{slo + 5000}ms"
			row.ok = False
			return row
		row.steps.append(_step("perception_select_component_foundation", env, ms))
		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		row.ok = ms <= slo
		if not row.ok:
			row.notes.append(f"select_slo ms={ms}>{slo}")
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		await _end(rt, str(sid) if sid else None)
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


async def board_soak(rt: Any, url: str, *, rounds: int = 3) -> BoardRow:
	row = BoardRow(id="soak_sessions")
	t0 = time.perf_counter()
	try:
		for i in range(rounds):
			intent = f"Soak round {i + 1}: surgical CSS hotfix observe homepage"
			env, ms = await _call(
				rt, "perception_session_start", {"base_url": url, "intent": intent}
			)
			row.steps.append(_step("perception_session_start", env, ms))
			sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
			if not sid:
				row.notes.append(f"round{i + 1}: no session_id")
				row.ok = False
				return row
			env, ms = await _call(
				rt,
				"perception_navigate_and_observe",
				{"session_id": sid, "url": "/", "include_screenshot": True},
			)
			row.steps.append(_step("perception_navigate_and_observe", env, ms))
			if not env.get("ok"):
				row.notes.append(f"round{i + 1}: observe failed")
			await _end(rt, str(sid))
		row.wall_ms = int((time.perf_counter() - t0) * 1000)
		row.ok = all(s.ok or s.tool == "perception_session_start" for s in row.steps) and all(
			s.slo_ok for s in row.steps
		)
		# session_start ok may be true even if; require observe oks
		obs = [s for s in row.steps if s.tool == "perception_navigate_and_observe"]
		row.ok = len(obs) == rounds and all(s.ok and s.slo_ok for s in obs)
		row.notes.append(f"rounds={rounds}")
	except Exception as exc:
		row.error = str(exc)
		row.ok = False
	finally:
		row.wall_ms = row.wall_ms or int((time.perf_counter() - t0) * 1000)
	return row


def write_slo_doc() -> None:
	lines = [
		"# Phase 3 — Latency / reliability SLOs",
		"",
		"**Date:** 2026-07-28",
		"**Board:** `scripts/eval_agent_face_phase3_reliability.py`",
		"",
		"## Tool wall-clock SLOs (local sandbox)",
		"",
		"| Tool | SLO (ms) |",
		"|------|----------|",
	]
	for k, v in SLO_MS.items():
		lines.append(f"| `{k}` | {v} |")
	lines += [
		"",
		"## Pass criteria",
		"",
		"1. `path_forms` / `path_hotfix` / `path_feature` → `data.verified=true`",
		"2. No false-green (`ok` without `verified` on required verify)",
		"3. `inspiration_bounded` / `select_bounded` return within SLO (hang = FAIL)",
		"4. Soak ≥3 sequential sessions without crash",
		"5. Feature class stable across observe (no host_action polish flip)",
		"",
		"## Non-goals",
		"",
		"- Inspiration provider perfection (degraded-but-bounded is OK)",
		"- Shrinking the 73-tool catalog",
		"",
	]
	SLO_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--url", default=DEFAULT_URL)
	parser.add_argument("--out", default=str(OUT))
	parser.add_argument("--soak-rounds", type=int, default=3)
	args = parser.parse_args()

	from navigation.core.scan_registry import ScanRegistry
	from navigation.core.snapshot_registry import SnapshotRegistry
	from navigation.execution_runtime.runtime import ExecutionRuntime, configure
	from navigation.visual_browser_intelligence.browser.session_store import SessionStore

	write_slo_doc()

	store = SessionStore(artifacts_root=ROOT / "artifacts" / "mcp-eval-phase3")
	runtime = ExecutionRuntime(store, ScanRegistry(), SnapshotRegistry())
	configure(runtime)

	print(f"Phase 3 reliability — url={args.url}")
	print("SLOs written →", SLO_DOC)
	print()

	boards = [
		board_forms,
		board_hotfix,
		board_feature,
		board_inspiration_bounded,
		board_select_bounded,
	]
	rows: list[BoardRow] = []
	try:
		for fn in boards:
			print(f"=== {fn.__name__} ===")
			row = await fn(runtime, args.url)
			rows.append(row)
			flag = "PASS" if row.ok else "FAIL"
			print(f"  {flag} wall={row.wall_ms}ms notes={row.notes} err={row.error}")
			for s in row.steps:
				print(
					f"    {s.tool} ok={s.ok} {s.latency_ms}ms "
					f"slo={'OK' if s.slo_ok else 'MISS'} class={s.card_class} "
					f"verified={s.verified}"
				)
			print()

		print("=== board_soak ===")
		soak = await board_soak(runtime, args.url, rounds=args.soak_rounds)
		rows.append(soak)
		print(f"  {'PASS' if soak.ok else 'FAIL'} wall={soak.wall_ms}ms notes={soak.notes}")
	finally:
		try:
			await asyncio.wait_for(store.end_all(), timeout=15.0)
		except Exception:
			pass

	passed = sum(1 for r in rows if r.ok)
	payload = {
		"suite": "agent_face_phase3_reliability",
		"url": args.url,
		"slos_ms": SLO_MS,
		"ok": passed == len(rows) and bool(rows),
		"passed": passed,
		"total": len(rows),
		"boards": [asdict(r) for r in rows],
	}
	Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(f"BOARD: {'PASS' if payload['ok'] else 'FAIL'} ({passed}/{len(rows)})")
	print("Wrote", args.out)
	return 0 if payload["ok"] else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
