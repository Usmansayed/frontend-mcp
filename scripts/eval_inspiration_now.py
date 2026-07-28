#!/usr/bin/env python3
"""Live eval: Inspiration Intelligence speed + reliability (current path).

Runs each grain twice (cold-ish + warm affinity/SERP), reports hit rate,
latency p50/p95, stop reasons, and provider mix.

Usage:
  PYTHONPATH=src python scripts/eval_inspiration_now.py
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

CASES: list[dict[str, Any]] = [
	{"name": "page/saas", "query": "modern saas landing page", "level": "standard", "min": 4},
	{"name": "page/dashboard", "query": "fintech dashboard analytics", "level": "standard", "min": 3},
	{"name": "section/pricing", "query": "pricing section cards", "level": "standard", "min": 4},
	{"name": "section/hero", "query": "hero section above the fold", "level": "standard", "min": 3},
	{"name": "component/navbar", "query": "navbar with mega menu", "level": "standard", "min": 4},
	{"name": "component/modal", "query": "modal dialog confirmation", "level": "standard", "min": 3},
	{"name": "chrome/button", "query": "primary button hover states", "level": "standard", "min": 3},
	{"name": "font/route", "query": "elegant serif display font", "level": "standard", "min": 0, "font": True},
	{"name": "level/light", "query": "website navigation header", "level": "light", "min": 3},
	{"name": "level/wide", "query": "b2b product marketing landing", "level": "wide", "min": 4, "web": True},
	{"name": "web/stress", "query": "neumorphic toast snackbar", "level": "standard", "min": 2},
	{"name": "pulse/equiv", "query": "saas pricing page", "level": "light", "min": 2, "web": True},
]

ROUNDS = 2
CASE_TIMEOUT = 28.0


@dataclass
class RunRow:
	name: str
	round: int
	ok: bool
	wall_s: float
	hits: int
	with_urls: int
	stop: str
	level: str
	providers: list[str] = field(default_factory=list)
	error: str = ""


def _pct(vals: list[float], p: float) -> float:
	if not vals:
		return 0.0
	s = sorted(vals)
	if len(s) == 1:
		return s[0]
	k = (len(s) - 1) * p
	f = int(k)
	c = min(f + 1, len(s) - 1)
	if f == c:
		return s[f]
	return s[f] + (s[c] - s[f]) * (k - f)


async def run_one(case: dict[str, Any], round_i: int) -> RunRow:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	name = str(case["name"])
	query = str(case["query"])
	level = str(case.get("level") or "standard")
	include_web = bool(case.get("web", True))
	t0 = time.perf_counter()
	try:
		manifest = await asyncio.wait_for(
			collect_inspiration_hits(
				query,
				inspiration_level=level,
				materialize_blobs=False,
				write_per_hit_files=False,
				include_live_sites=False,
				include_web_search=include_web,
				max_web_screenshots=0,
				use_result_cache=False,
				use_multi_scout=level not in {"light"},
			),
			timeout=CASE_TIMEOUT,
		)
	except asyncio.TimeoutError:
		return RunRow(
			name=name,
			round=round_i,
			ok=False,
			wall_s=round(time.perf_counter() - t0, 3),
			hits=0,
			with_urls=0,
			stop="TIMEOUT",
			level=level,
			error=f">{CASE_TIMEOUT}s",
		)
	except Exception as exc:  # noqa: BLE001
		return RunRow(
			name=name,
			round=round_i,
			ok=False,
			wall_s=round(time.perf_counter() - t0, 3),
			hits=0,
			with_urls=0,
			stop="ERROR",
			level=level,
			error=f"{type(exc).__name__}: {exc}",
		)

	wall = round(time.perf_counter() - t0, 3)
	hits = list(manifest.get("hits") or [])
	n = int(manifest.get("total_hits") or len(hits))
	with_urls = int(manifest.get("total_with_urls") or sum(1 for h in hits if h.get("preview_url") or h.get("agent_view_url")))
	stop = str(manifest.get("stop_reason") or "")
	providers = sorted({str(h.get("provider_id") or "") for h in hits if h.get("provider_id")})
	ok = True
	if case.get("font"):
		font = (manifest.get("pattern") or {}).get("font_route")
		ok = bool(font) and stop == "font_routed_to_resource_intelligence"
	else:
		ok = n >= int(case.get("min") or 0) and with_urls >= int(case.get("min") or 0)

	return RunRow(
		name=name,
		round=round_i,
		ok=ok,
		wall_s=wall,
		hits=n,
		with_urls=with_urls,
		stop=stop,
		level=level,
		providers=providers[:10],
	)


async def main() -> int:
	print("=" * 78)
	print("INSPIRATION INTELLIGENCE — SPEED + RELIABILITY EVAL")
	print(f"cases={len(CASES)}  rounds={ROUNDS}  timeout/case={CASE_TIMEOUT}s")
	print("=" * 78)

	rows: list[RunRow] = []
	t_all = time.perf_counter()
	for r in range(1, ROUNDS + 1):
		print(f"\n--- ROUND {r}/{ROUNDS} ---")
		for case in CASES:
			row = await run_one(case, r)
			rows.append(row)
			mark = "PASS" if row.ok else "FAIL"
			print(
				f"  [{mark}] {row.name:22} {row.wall_s:5.2f}s  hits={row.hits:2}  "
				f"urls={row.with_urls:2}  stop={row.stop or '-'!r}"
			)
			if row.error:
				print(f"         ERROR {row.error}")

	total_wall = round(time.perf_counter() - t_all, 2)
	ok_n = sum(1 for x in rows if x.ok)
	fail_n = len(rows) - ok_n
	walls = [x.wall_s for x in rows if x.stop != "ERROR"]
	pass_walls = [x.wall_s for x in rows if x.ok]
	hit_counts = [x.hits for x in rows if not any(c.get("font") and c["name"] == x.name for c in CASES)]

	# Per-case reliability across rounds
	by_name: dict[str, list[RunRow]] = {}
	for x in rows:
		by_name.setdefault(x.name, []).append(x)

	print("\n" + "=" * 78)
	print("PER-CASE RELIABILITY")
	print("=" * 78)
	fragile: list[str] = []
	for name, group in by_name.items():
		passed = sum(1 for g in group if g.ok)
		avg_w = statistics.mean(g.wall_s for g in group)
		avg_h = statistics.mean(g.hits for g in group)
		rate = passed / len(group)
		flag = "OK" if rate == 1.0 else ("WEAK" if rate >= 0.5 else "BAD")
		if rate < 1.0:
			fragile.append(name)
		print(
			f"  {flag:4} {name:22}  {passed}/{len(group)}  "
			f"avg={avg_w:5.2f}s  hits≈{avg_h:4.1f}"
		)

	print("\n" + "=" * 78)
	print("SPEED SUMMARY")
	print("=" * 78)
	print(f"  runs            {len(rows)}")
	print(f"  pass rate       {ok_n}/{len(rows)} ({100.0 * ok_n / len(rows):.1f}%)")
	print(f"  suite wall      {total_wall}s")
	print(f"  latency p50     {_pct(walls, 0.50):.2f}s")
	print(f"  latency p95     {_pct(walls, 0.95):.2f}s")
	print(f"  latency max     {max(walls) if walls else 0:.2f}s")
	print(f"  pass latency µ  {statistics.mean(pass_walls) if pass_walls else 0:.2f}s")
	print(f"  under 1s        {sum(1 for w in walls if w < 1.0)}/{len(walls)}")
	print(f"  under 3s        {sum(1 for w in walls if w < 3.0)}/{len(walls)}")
	print(f"  under 5s        {sum(1 for w in walls if w < 5.0)}/{len(walls)}")
	if hit_counts:
		print(f"  hits median     {statistics.median(hit_counts):.0f}")

	# Grade
	rate = ok_n / max(1, len(rows))
	p95 = _pct(walls, 0.95)
	if rate >= 0.95 and p95 <= 5.0:
		grade = "A — production-ready for agent collect"
	elif rate >= 0.85 and p95 <= 8.0:
		grade = "B — solid; watch fragile grains"
	elif rate >= 0.7:
		grade = "C — usable with widen/retry"
	else:
		grade = "D — not reliable enough yet"

	print("\n" + "=" * 78)
	print(f"VERDICT  {grade}")
	if fragile:
		print(f"FRAGILE  {', '.join(fragile)}")
	else:
		print("FRAGILE  none")
	print("=" * 78)

	out = {
		"pass_rate": round(rate, 3),
		"passed": ok_n,
		"failed": fail_n,
		"total": len(rows),
		"suite_wall_s": total_wall,
		"p50_s": round(_pct(walls, 0.50), 3),
		"p95_s": round(_pct(walls, 0.95), 3),
		"max_s": round(max(walls), 3) if walls else 0,
		"grade": grade,
		"fragile": fragile,
		"rows": [asdict(r) for r in rows],
	}
	print("\nJSON:" + json.dumps(out, ensure_ascii=True))
	return 0 if fail_n == 0 else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
