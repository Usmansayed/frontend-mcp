"""Inspiration speed board — Phases A–E.

Goal: prove inspiration is fast enough to call again and again as a core MCP loop.

Targets:
  A cold collect p50  ≤ 3.0s  (≥3 hits)
  A warm collect p50  ≤ 1.5s
  B parallel 3        ≤ 5.0s wall
  B sequential 5-pack ≤ 12.0s total wall
  C quality@speed     each case hits + provider gate within hard wall
  D cache ×3          cached ≪ cold (≥3× or ≤400ms) + pool-only warm
  E no Stealthy       friendly CDN path never consumes Stealthy budget

Usage:
  PYTHONPATH=src python -u scripts/eval_inspiration_speed_board.py
  PYTHONPATH=src python -u scripts/eval_inspiration_speed_board.py --phases d,e
  PYTHONPATH=src python -u scripts/eval_inspiration_speed_board.py --phases a,b,c,d,e
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

# --- budgets ---
COLD_P50_S = 3.0
WARM_P50_S = 1.5
PARALLEL_WALL_S = 5.0
SEQUENTIAL_PACK_S = 12.0
MIN_HITS = 3
CASE_TIMEOUT_S = 12.0
CACHE_WARM_BUDGET_S = 0.4
CACHE_SPEEDUP_MIN = 3.0
PHASE_D_QUERY = "pricing section cards"
PHASE_D_REPEATS = 3
FRIENDLY_CDN_URLS = (
	"https://www.saasframe.io/categories/login",
	"https://img.daisyui.com/images/components/input.webp",
	"https://hero.gallery/",
	"https://www.footer.design/",
)
WAF_HOST_URL = "https://dribbble.com/search/login"

PHASE_A_CASES: list[dict[str, Any]] = [
	{"id": "landing", "query": "modern saas landing page", "level": "light"},
	{"id": "pricing", "query": "pricing section cards", "level": "light"},
	{"id": "navbar", "query": "navbar with mega menu", "level": "light"},
	{"id": "login", "query": "login form saas", "level": "light"},
	{"id": "button", "query": "primary button ui", "level": "light"},
]

WARM_IDS = ("landing", "pricing", "navbar")

PARALLEL_QUERIES = [
	"modern saas landing page",
	"pricing section cards",
	"login form saas",
]

SEQUENTIAL_QUERIES = [
	"modern saas landing page",
	"pricing section cards",
	"navbar with mega menu",
	"login form saas",
	"primary button ui",
]

# Phase C — quality under hard walls (tighter than old 15–22s batteries)
PHASE_C_CASES: list[dict[str, Any]] = [
	{
		"id": "forms/login",
		"query": "login signup form with email password",
		"level": "standard",
		"min_hits": 3,
		"budget_s": 8.0,
		"expect_provider_any": [
			"daisyui",
			"saasframe_login",
			"saasframe_signup",
			"nicelydone_auth",
			"web_search",
		],
	},
	{
		"id": "forms/checkout",
		"query": "checkout payment form multi step",
		"level": "standard",
		"min_hits": 3,
		"budget_s": 8.0,
		"expect_provider_any": ["daisyui", "saasframe_checkout", "saasframe", "web_search"],
	},
	{
		"id": "chrome/text_input",
		"query": "text input with label and placeholder",
		"level": "standard",
		"min_hits": 3,
		"budget_s": 6.0,
		"expect_provider_any": ["daisyui", "web_search"],
	},
	{
		"id": "section/hero",
		"query": "hero section above the fold",
		"level": "standard",
		"min_hits": 3,
		"budget_s": 8.0,
		"expect_provider_any": [
			"daisyui",
			"saasframe",
			"saaslandingpage",
			"web_search",
			"hero_gallery",
		],
	},
	{
		"id": "section/footer",
		"query": "site footer links",
		"level": "light",
		"min_hits": 3,
		"budget_s": 5.0,
		"expect_provider_any": ["footer_design", "daisyui"],
		"web": False,
	},
	{
		"id": "chrome/button",
		"query": "primary button hover states",
		"level": "standard",
		"min_hits": 3,
		"budget_s": 6.0,
		"expect_provider_any": [
			"daisyui",
			"aceternity_buttons",
			"shadcnblocks",
			"ibelick_buttons",
			"web_search",
		],
	},
]


@dataclass
class RunRow:
	phase: str
	case_id: str
	query: str
	ok: bool
	wall_s: float
	hits: int = 0
	providers: list[str] = field(default_factory=list)
	stop: str = ""
	error: str = ""
	cached: bool = False
	budget_s: float | None = None
	budget_ok: bool | None = None
	notes: list[str] = field(default_factory=list)
	cache_hit: bool = False
	stealthy_used: bool = False


def log(msg: str) -> None:
	print(msg, flush=True)


def _stealthy_signals(manifest: dict[str, Any]) -> list[str]:
	"""Detect Stealthy usage from manifest (degraded / fetch_tier / notes)."""
	signals: list[str] = []
	for hit in manifest.get("hits") or []:
		tier = str(hit.get("fetch_tier") or "").lower()
		if "stealthy" in tier or "scrapling_stealthy" in tier:
			signals.append(f"tier:{tier}")
		for d in hit.get("degraded") or []:
			ds = str(d).lower()
			if "stealthy" in ds:
				signals.append(f"degraded:{ds}")
	for row in manifest.get("provider_summary") or []:
		if isinstance(row, dict):
			blob = json.dumps(row).lower()
			if "stealthy" in blob:
				signals.append("provider_summary:stealthy")
				break
		elif "stealthy" in str(row).lower():
			signals.append("provider_summary:stealthy")
			break
	for note in manifest.get("reuse_notes") or []:
		if "stealthy" in str(note).lower():
			signals.append(f"reuse:{note}")
	return signals[:8]


async def _collect_one(
	query: str,
	*,
	level: str = "light",
	use_result_cache: bool = False,
	timeout_s: float = CASE_TIMEOUT_S,
	include_web_search: bool | None = None,
	use_multi_scout: bool | None = None,
	min_hits: int = MIN_HITS,
) -> dict[str, Any]:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	t0 = time.perf_counter()
	try:
		manifest = await asyncio.wait_for(
			collect_inspiration_hits(
				query,
				inspiration_level=level,
				materialize_blobs=False,
				write_per_hit_files=False,
				include_live_sites=False,
				include_web_search=include_web_search,
				max_web_screenshots=0,
				use_result_cache=use_result_cache,
				use_multi_scout=use_multi_scout,
			),
			timeout=timeout_s,
		)
		hits = list(manifest.get("hits") or [])
		n = int(manifest.get("total_hits") or len(hits))
		providers = sorted(
			{str(h.get("provider_id") or "") for h in hits if h.get("provider_id")}
		)
		stealthy_sigs = _stealthy_signals(manifest)
		return {
			"ok": n >= min_hits,
			"wall_s": round(time.perf_counter() - t0, 3),
			"hits": n,
			"providers": providers[:12],
			"stop": str(manifest.get("stop_reason") or ""),
			"error": "",
			"cache_hit": bool(manifest.get("cache_hit")),
			"stealthy_signals": stealthy_sigs,
			"stealthy_used": bool(stealthy_sigs),
		}
	except asyncio.TimeoutError:
		return {
			"ok": False,
			"wall_s": round(time.perf_counter() - t0, 3),
			"hits": 0,
			"providers": [],
			"stop": "",
			"error": f"TIMEOUT>{timeout_s}s",
			"cache_hit": False,
			"stealthy_signals": [],
			"stealthy_used": False,
		}
	except Exception as exc:  # noqa: BLE001
		return {
			"ok": False,
			"wall_s": round(time.perf_counter() - t0, 3),
			"hits": 0,
			"providers": [],
			"stop": "",
			"error": f"{type(exc).__name__}:{exc}"[:200],
			"cache_hit": False,
			"stealthy_signals": [],
			"stealthy_used": False,
		}


def _p50(vals: list[float]) -> float | None:
	if not vals:
		return None
	return round(statistics.median(vals), 3)


async def phase_a() -> tuple[list[RunRow], dict[str, Any]]:
	"""Cold board + warm repeats."""
	log("=" * 72)
	log("PHASE A — baseline speed board (cold then warm)")
	log("=" * 72)
	os.environ.setdefault("INSPIRATION_FAST", "1")

	rows: list[RunRow] = []

	log("\n-- cold (use_result_cache=False) --")
	for case in PHASE_A_CASES:
		cid, q, level = case["id"], case["query"], case["level"]
		log(f"\n>> cold/{cid} {q!r}")
		r = await _collect_one(q, level=level, use_result_cache=False)
		row = RunRow(
			phase="A_cold",
			case_id=cid,
			query=q,
			ok=bool(r["ok"]),
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			cached=False,
			budget_s=COLD_P50_S,
			budget_ok=float(r["wall_s"]) <= COLD_P50_S,
		)
		rows.append(row)
		log(
			f"   ok={row.ok} hits={row.hits} wall={row.wall_s:.3f}s "
			f"budget={'PASS' if row.budget_ok else 'SLOW'} providers={row.providers} {row.error}"
		)

	log("\n-- warm (use_result_cache=True, repeat) --")
	by_id = {c["id"]: c for c in PHASE_A_CASES}
	for cid in WARM_IDS:
		case = by_id[cid]
		q, level = case["query"], case["level"]
		log(f"\n>> warm/{cid} {q!r}")
		r = await _collect_one(q, level=level, use_result_cache=True)
		row = RunRow(
			phase="A_warm",
			case_id=cid,
			query=q,
			ok=bool(r["ok"]),
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			cached=True,
			budget_s=WARM_P50_S,
			budget_ok=float(r["wall_s"]) <= WARM_P50_S,
		)
		rows.append(row)
		log(
			f"   ok={row.ok} hits={row.hits} wall={row.wall_s:.3f}s "
			f"budget={'PASS' if row.budget_ok else 'SLOW'} providers={row.providers} {row.error}"
		)

	cold_walls = [r.wall_s for r in rows if r.phase == "A_cold" and r.ok]
	warm_walls = [r.wall_s for r in rows if r.phase == "A_warm" and r.ok]
	cold_ok_n = sum(1 for r in rows if r.phase == "A_cold" and r.ok)
	warm_ok_n = sum(1 for r in rows if r.phase == "A_warm" and r.ok)
	summary = {
		"cold_ok": cold_ok_n,
		"cold_total": sum(1 for r in rows if r.phase == "A_cold"),
		"cold_p50_s": _p50(cold_walls),
		"cold_max_s": round(max(cold_walls), 3) if cold_walls else None,
		"cold_budget_s": COLD_P50_S,
		"cold_budget_pass": bool(cold_walls) and (_p50(cold_walls) or 9e9) <= COLD_P50_S,
		"warm_ok": warm_ok_n,
		"warm_total": sum(1 for r in rows if r.phase == "A_warm"),
		"warm_p50_s": _p50(warm_walls),
		"warm_max_s": round(max(warm_walls), 3) if warm_walls else None,
		"warm_budget_s": WARM_P50_S,
		"warm_budget_pass": bool(warm_walls) and (_p50(warm_walls) or 9e9) <= WARM_P50_S,
		"all_quality_pass": cold_ok_n == 5 and warm_ok_n == 3,
	}
	log("\nPHASE A SUMMARY: " + json.dumps(summary))
	return rows, summary


async def phase_b() -> tuple[list[RunRow], dict[str, Any]]:
	"""Parallel fan-out + sequential agent-loop pack."""
	log("\n" + "=" * 72)
	log("PHASE B — concurrency stress")
	log("=" * 72)
	os.environ.setdefault("INSPIRATION_FAST", "1")
	rows: list[RunRow] = []

	log("\n-- parallel ×3 --")
	t0 = time.perf_counter()
	results = await asyncio.gather(
		*[_collect_one(q, level="light", use_result_cache=False) for q in PARALLEL_QUERIES]
	)
	parallel_wall = round(time.perf_counter() - t0, 3)
	for q, r in zip(PARALLEL_QUERIES, results, strict=True):
		row = RunRow(
			phase="B_parallel",
			case_id=q.split()[0],
			query=q,
			ok=bool(r["ok"]),
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
		)
		rows.append(row)
		log(
			f"   {q!r} ok={row.ok} hits={row.hits} self_wall={row.wall_s:.3f}s "
			f"providers={row.providers} {row.error}"
		)
	log(f"   PARALLEL wall={parallel_wall:.3f}s budget={PARALLEL_WALL_S}s")

	log("\n-- sequential ×5 (agent loop) --")
	t0 = time.perf_counter()
	seq_ok = 0
	for q in SEQUENTIAL_QUERIES:
		r = await _collect_one(q, level="light", use_result_cache=True)
		row = RunRow(
			phase="B_sequential",
			case_id=q.split()[0],
			query=q,
			ok=bool(r["ok"]),
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			cached=True,
		)
		rows.append(row)
		if row.ok:
			seq_ok += 1
		log(
			f"   {q!r} ok={row.ok} hits={row.hits} wall={row.wall_s:.3f}s "
			f"providers={row.providers} {row.error}"
		)
	sequential_wall = round(time.perf_counter() - t0, 3)
	log(f"   SEQUENTIAL pack wall={sequential_wall:.3f}s budget={SEQUENTIAL_PACK_S}s")

	par_ok = sum(1 for r in rows if r.phase == "B_parallel" and r.ok)
	summary = {
		"parallel_ok": par_ok,
		"parallel_total": 3,
		"parallel_wall_s": parallel_wall,
		"parallel_budget_s": PARALLEL_WALL_S,
		"parallel_budget_pass": parallel_wall <= PARALLEL_WALL_S and par_ok == 3,
		"sequential_ok": seq_ok,
		"sequential_total": 5,
		"sequential_wall_s": sequential_wall,
		"sequential_budget_s": SEQUENTIAL_PACK_S,
		"sequential_budget_pass": sequential_wall <= SEQUENTIAL_PACK_S and seq_ok == 5,
	}
	log("\nPHASE B SUMMARY: " + json.dumps(summary))
	return rows, summary


async def phase_c() -> tuple[list[RunRow], dict[str, Any]]:
	"""Quality under hard wall budgets (forms / sections / chrome)."""
	log("\n" + "=" * 72)
	log("PHASE C — quality @ speed (hard walls)")
	log("=" * 72)
	os.environ.setdefault("INSPIRATION_FAST", "1")
	rows: list[RunRow] = []

	for case in PHASE_C_CASES:
		cid = str(case["id"])
		q = str(case["query"])
		level = str(case.get("level") or "standard")
		budget = float(case["budget_s"])
		min_hits = int(case.get("min_hits") or MIN_HITS)
		want_any = list(case.get("expect_provider_any") or [])
		web = case.get("web")
		if web is False:
			include_web: bool | None = False
		elif web is True:
			include_web = True
		else:
			include_web = None

		log(f"\n>> {cid} {q!r} budget≤{budget}s level={level}")
		r = await _collect_one(
			q,
			level=level,
			use_result_cache=False,
			timeout_s=budget + 0.5,
			include_web_search=include_web,
			use_multi_scout=False if level == "light" else None,
			min_hits=min_hits,
		)
		notes: list[str] = []
		quality_ok = bool(r["ok"])
		if want_any and not any(p in r["providers"] for p in want_any):
			quality_ok = False
			notes.append(f"providers {r['providers']} miss any of {want_any}")
		budget_ok = float(r["wall_s"]) <= budget and not str(r["error"]).startswith("TIMEOUT")
		ok = quality_ok and budget_ok
		if not budget_ok:
			notes.append(f"wall {r['wall_s']}s > budget {budget}s")
		row = RunRow(
			phase="C_quality",
			case_id=cid,
			query=q,
			ok=ok,
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			budget_s=budget,
			budget_ok=budget_ok,
			notes=notes,
		)
		rows.append(row)
		log(
			f"   ok={row.ok} quality={quality_ok} budget={'PASS' if budget_ok else 'FAIL'} "
			f"hits={row.hits} wall={row.wall_s:.3f}s providers={row.providers} "
			f"{row.error} {notes}"
		)

	ok_n = sum(1 for r in rows if r.ok)
	summary = {
		"ok": ok_n,
		"total": len(rows),
		"all_pass": ok_n == len(rows),
		"failed": [r.case_id for r in rows if not r.ok],
		"p50_s": _p50([r.wall_s for r in rows if r.ok]),
		"max_s": round(max((r.wall_s for r in rows), default=0), 3),
	}
	log("\nPHASE C SUMMARY: " + json.dumps(summary))
	return rows, summary


async def phase_d() -> tuple[list[RunRow], dict[str, Any]]:
	"""Cache / repeatability: result-cache ×3 vs pool-only warm ×3."""
	log("\n" + "=" * 72)
	log("PHASE D — cache / repeatability")
	log("=" * 72)
	os.environ.setdefault("INSPIRATION_FAST", "1")
	from navigation.inspiration_intelligence.result_cache import clear_result_cache

	clear_result_cache()
	rows: list[RunRow] = []
	q = PHASE_D_QUERY

	log(f"\n-- result-cache ON ×{PHASE_D_REPEATS} ({q!r}) --")
	cached_walls: list[float] = []
	for i in range(1, PHASE_D_REPEATS + 1):
		r = await _collect_one(q, level="light", use_result_cache=True)
		is_seed = i == 1
		notes: list[str] = []
		if is_seed:
			budget_ok = bool(r["ok"]) and not str(r["error"]).startswith("TIMEOUT")
			notes.append("seed")
		else:
			# Warm: cache hit and cheap (≤400ms) OR ≥3× vs seed.
			notes.append("warm_cache")
			if not r.get("cache_hit"):
				notes.append("expected cache_hit")
			speed_ok = float(r["wall_s"]) <= CACHE_WARM_BUDGET_S
			budget_ok = (
				bool(r["ok"])
				and bool(r.get("cache_hit"))
				and speed_ok
				and not str(r["error"]).startswith("TIMEOUT")
			)
			cached_walls.append(float(r["wall_s"]))
		ok = budget_ok
		# Seed always marks ok from budget_ok; warm rows may flip after speedup check below.
		row = RunRow(
			phase="D_cache_on",
			case_id=f"cache_on_{i}",
			query=q,
			ok=ok,
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			cached=True,
			budget_s=None if is_seed else CACHE_WARM_BUDGET_S,
			budget_ok=budget_ok if not is_seed else None,
			notes=notes,
			cache_hit=bool(r.get("cache_hit")),
		)
		rows.append(row)
		log(
			f"   #{i} ok={row.ok} cache_hit={row.cache_hit} hits={row.hits} "
			f"wall={row.wall_s:.3f}s {notes} {row.error}"
		)

	cold_seed = next((r.wall_s for r in rows if r.case_id == "cache_on_1"), None)
	warm_p50 = _p50(cached_walls)
	speedup = None
	if cold_seed and warm_p50 and warm_p50 > 0:
		speedup = round(cold_seed / warm_p50, 2)

	def _warm_fast_enough(wall: float) -> bool:
		if wall <= CACHE_WARM_BUDGET_S:
			return True
		return (
			cold_seed is not None
			and cold_seed >= 0.05
			and wall > 0
			and (cold_seed / wall) >= CACHE_SPEEDUP_MIN
		)

	# Reconcile warm row ok with ≤400ms OR ≥3× seed rule.
	for row in rows:
		if row.phase != "D_cache_on" or row.case_id == "cache_on_1":
			continue
		fast = _warm_fast_enough(row.wall_s)
		row.budget_ok = fast
		row.ok = bool(row.hits >= MIN_HITS and row.cache_hit and fast and not row.error)
		if fast and row.wall_s > CACHE_WARM_BUDGET_S:
			row.notes = list(row.notes) + [f"speedup_ok_vs_seed"]

	warm_pass = bool(cached_walls) and all(_warm_fast_enough(w) for w in cached_walls)
	cache_hits_ok = all(
		r.cache_hit for r in rows if r.phase == "D_cache_on" and r.case_id != "cache_on_1"
	)
	seed_ok = any(r.ok and r.case_id == "cache_on_1" for r in rows)

	log(f"\n-- result-cache OFF ×{PHASE_D_REPEATS} (pool-only warm) --")
	pool_walls: list[float] = []
	for i in range(1, PHASE_D_REPEATS + 1):
		r = await _collect_one(q, level="light", use_result_cache=False)
		pool_walls.append(float(r["wall_s"]))
		ok = bool(r["ok"]) and not str(r["error"]).startswith("TIMEOUT")
		row = RunRow(
			phase="D_cache_off",
			case_id=f"cache_off_{i}",
			query=q,
			ok=ok,
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			cached=False,
			notes=["pool_warm"],
			cache_hit=bool(r.get("cache_hit")),
		)
		rows.append(row)
		log(
			f"   #{i} ok={row.ok} cache_hit={row.cache_hit} hits={row.hits} "
			f"wall={row.wall_s:.3f}s {row.error}"
		)

	pool_ok = sum(1 for r in rows if r.phase == "D_cache_off" and r.ok) == PHASE_D_REPEATS
	summary = {
		"seed_ok": seed_ok,
		"seed_wall_s": cold_seed,
		"warm_cache_p50_s": warm_p50,
		"warm_cache_budget_s": CACHE_WARM_BUDGET_S,
		"warm_cache_pass": warm_pass and cache_hits_ok,
		"cache_hits_ok": cache_hits_ok,
		"speedup_vs_seed": speedup,
		"pool_ok": pool_ok,
		"pool_p50_s": _p50(pool_walls),
		"pool_max_s": round(max(pool_walls), 3) if pool_walls else None,
		"all_pass": bool(seed_ok and warm_pass and cache_hits_ok and pool_ok),
	}
	log("\nPHASE D SUMMARY: " + json.dumps(summary))
	return rows, summary


async def phase_e() -> tuple[list[RunRow], dict[str, Any]]:
	"""Failure routing: friendly CDNs never take Stealthy; WAF host remains eligible."""
	log("\n" + "=" * 72)
	log("PHASE E — failure routing (no Stealthy on friendly CDN)")
	log("=" * 72)
	os.environ.setdefault("INSPIRATION_FAST", "1")
	from navigation.inspiration_intelligence.browser import stealthy_fallback as sf
	from navigation.inspiration_intelligence.browser.scrapling_route import should_try_stealthy

	sf.reset_stealthy_budget_for_tests()
	rows: list[RunRow] = []
	notes_all: list[str] = []

	policy_ok = True
	for url in FRIENDLY_CDN_URLS:
		allowed = should_try_stealthy(url, blocked=True, fast_mode=True)
		ok = not allowed
		if not ok:
			policy_ok = False
			notes_all.append(f"policy_leak:{url}")
		rows.append(
			RunRow(
				phase="E_policy",
				case_id="friendly_deny",
				query=url,
				ok=ok,
				wall_s=0.0,
				notes=["should_try_stealthy=False"],
			)
		)
		log(f"   policy friendly deny {url!r} ok={ok}")

	waf_ok = should_try_stealthy(WAF_HOST_URL, blocked=True, fast_mode=True)
	rows.append(
		RunRow(
			phase="E_policy",
			case_id="waf_eligible",
			query=WAF_HOST_URL,
			ok=bool(waf_ok),
			wall_s=0.0,
			notes=["should_try_stealthy=True (policy only, not invoked)"],
		)
	)
	log(f"   policy waf eligible {WAF_HOST_URL!r} ok={bool(waf_ok)}")
	if not waf_ok:
		policy_ok = False
		notes_all.append("waf_not_eligible")

	sf.reset_stealthy_budget_for_tests()
	before = sf.stealthy_budget_remaining()
	log("\n-- live friendly collect (light landing) --")
	r = await _collect_one(
		"modern saas landing page",
		level="light",
		use_result_cache=False,
		use_multi_scout=False,
	)
	after = sf.stealthy_budget_remaining()
	budget_untouched = before == after
	no_stealthy_in_manifest = not bool(r.get("stealthy_used"))
	live_ok = (
		bool(r["ok"])
		and budget_untouched
		and no_stealthy_in_manifest
		and not str(r["error"]).startswith("TIMEOUT")
	)
	live_notes: list[str] = []
	if not budget_untouched:
		live_notes.append(f"budget {before}->{after}")
	if r.get("stealthy_signals"):
		live_notes.append(f"signals={r['stealthy_signals']}")
	rows.append(
		RunRow(
			phase="E_live",
			case_id="friendly_collect",
			query="modern saas landing page",
			ok=live_ok,
			wall_s=float(r["wall_s"]),
			hits=int(r["hits"]),
			providers=list(r["providers"]),
			stop=str(r["stop"]),
			error=str(r["error"]),
			notes=live_notes or ["budget_untouched", "no_stealthy_signals"],
			stealthy_used=bool(r.get("stealthy_used")),
		)
	)
	log(
		f"   live ok={live_ok} hits={r['hits']} wall={r['wall_s']:.3f}s "
		f"budget={before}->{after} stealthy={r.get('stealthy_used')} "
		f"providers={r['providers']} {live_notes}"
	)

	rows.append(
		RunRow(
			phase="E_waf_optional",
			case_id="waf_policy_only",
			query=WAF_HOST_URL,
			ok=True,
			wall_s=0.0,
			notes=["slow_path_excluded_from_p50", "stealthy_not_invoked"],
		)
	)

	summary = {
		"policy_ok": policy_ok and bool(waf_ok),
		"live_friendly_ok": live_ok,
		"stealthy_budget_before": before,
		"stealthy_budget_after": after,
		"stealthy_budget_untouched": budget_untouched,
		"live_wall_s": float(r["wall_s"]),
		"live_hits": int(r["hits"]),
		"all_pass": bool(policy_ok and waf_ok and live_ok),
		"notes": notes_all,
	}
	log("\nPHASE E SUMMARY: " + json.dumps(summary))
	return rows, summary


_ALL_PHASES = frozenset({"a", "b", "c", "d", "e"})
_ROW_PHASE_KEYS = {
	"a": {"A_cold", "A_warm"},
	"b": {"B_parallel", "B_sequential"},
	"c": {"C_quality"},
	"d": {"D_cache_on", "D_cache_off"},
	"e": {"E_policy", "E_live", "E_waf_optional"},
}


async def main_async(phases: set[str]) -> int:
	log(f"INSPIRATION SPEED BOARD — phases={sorted(phases)}")
	os.environ.setdefault("INSPIRATION_FAST", "1")

	report_path = Path("docs/research/inspiration_speed_board.json")
	prev: dict[str, Any] = {}
	if report_path.exists() and phases != _ALL_PHASES:
		try:
			prev = json.loads(report_path.read_text(encoding="utf-8"))
		except Exception:
			prev = {}

	all_rows: list[RunRow] = []
	a_sum = prev.get("phase_a") or {}
	b_sum = prev.get("phase_b") or {}
	c_sum = prev.get("phase_c") or {}
	d_sum = prev.get("phase_d") or {}
	e_sum = prev.get("phase_e") or {}

	if "a" in phases:
		a_rows, a_sum = await phase_a()
		all_rows.extend(a_rows)
	if "b" in phases:
		b_rows, b_sum = await phase_b()
		all_rows.extend(b_rows)
	if "c" in phases:
		c_rows, c_sum = await phase_c()
		all_rows.extend(c_rows)
	if "d" in phases:
		d_rows, d_sum = await phase_d()
		all_rows.extend(d_rows)
	if "e" in phases:
		e_rows, e_sum = await phase_e()
		all_rows.extend(e_rows)

	# Score only phases executed this run (subset runs don't inherit prior fails).
	checks: list[bool] = []
	if "a" in phases:
		checks.extend(
			[
				bool(a_sum.get("cold_budget_pass")),
				bool(a_sum.get("warm_budget_pass")),
				bool(a_sum.get("all_quality_pass")),
			]
		)
	if "b" in phases:
		checks.extend(
			[
				bool(b_sum.get("parallel_budget_pass")),
				bool(b_sum.get("sequential_budget_pass")),
			]
		)
	if "c" in phases:
		checks.append(bool(c_sum.get("all_pass")))
	if "d" in phases:
		checks.append(bool(d_sum.get("all_pass")))
	if "e" in phases:
		checks.append(bool(e_sum.get("all_pass")))
	board_pass = all(checks) if checks else False

	merged_rows = list(prev.get("rows") or [])
	if all_rows:
		keep_phases: set[str] = set()
		for key, labels in _ROW_PHASE_KEYS.items():
			if key not in phases:
				keep_phases.update(labels)
		merged_rows = [r for r in merged_rows if r.get("phase") in keep_phases]
		merged_rows.extend(asdict(r) for r in all_rows)

	# Full-board green only when every phase summary is present and passing.
	full_summaries = [a_sum, b_sum, c_sum, d_sum, e_sum]
	full_board_pass = all(
		[
			bool(a_sum.get("cold_budget_pass")),
			bool(a_sum.get("warm_budget_pass")),
			bool(a_sum.get("all_quality_pass")),
			bool(b_sum.get("parallel_budget_pass")),
			bool(b_sum.get("sequential_budget_pass")),
			bool(c_sum.get("all_pass")),
			bool(d_sum.get("all_pass")),
			bool(e_sum.get("all_pass")),
		]
	) if all(full_summaries) else False

	out = {
		"board_pass": False,  # set below
		"subset_pass": board_pass,
		"full_board_pass": full_board_pass,
		"phases_run": sorted(phases),
		"targets": {
			"cold_p50_s": COLD_P50_S,
			"warm_p50_s": WARM_P50_S,
			"parallel_wall_s": PARALLEL_WALL_S,
			"sequential_pack_s": SEQUENTIAL_PACK_S,
			"min_hits": MIN_HITS,
			"cache_warm_budget_s": CACHE_WARM_BUDGET_S,
			"cache_speedup_min": CACHE_SPEEDUP_MIN,
			"phase_c_budgets": {c["id"]: c["budget_s"] for c in PHASE_C_CASES},
		},
		"phase_a": a_sum,
		"phase_b": b_sum,
		"phase_c": c_sum,
		"phase_d": d_sum,
		"phase_e": e_sum,
		"rows": merged_rows,
	}

	exit_pass = full_board_pass if phases == set(_ALL_PHASES) else board_pass
	out["board_pass"] = exit_pass

	log("\n" + "=" * 72)
	log(f"BOARD PASS: {exit_pass}")
	log("=" * 72)
	log(
		json.dumps(
			{
				"phases_run": sorted(phases),
				"phase_d": d_sum,
				"phase_e": e_sum,
				"phase_a": a_sum,
				"phase_b": b_sum,
				"phase_c": c_sum,
				"subset_pass": board_pass,
				"full_board_pass": full_board_pass,
				"board_pass": exit_pass,
			},
			indent=2,
		)
	)

	report_path.parent.mkdir(parents=True, exist_ok=True)
	report_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
	log(f"Wrote {report_path}")
	return 0 if exit_pass else 1


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"--phases",
		default="a,b,c,d,e",
		help="Comma list: a,b,c,d,e (default all). Example: --phases d,e",
	)
	args = parser.parse_args()
	phases = {p.strip().lower() for p in str(args.phases).split(",") if p.strip()}
	phases &= set(_ALL_PHASES)
	if not phases:
		phases = set(_ALL_PHASES)
	return asyncio.run(main_async(phases))


if __name__ == "__main__":
	raise SystemExit(main())
