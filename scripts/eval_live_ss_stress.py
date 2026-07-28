#!/usr/bin/env python3
"""Stress eval for live Chromium / WAF harden path (bounded).

Uses short capture timeouts + soft famous sites. Does not require SS success —
asserts collect still returns HTTP packs and never hangs past case timeout.

Usage:
  PYTHONPATH=src INSPIRATION_HEADED_RETRY=0 INSPIRATION_LIVE_CAPTURE_TIMEOUT_S=6 \\
    python scripts/eval_live_ss_stress.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("INSPIRATION_HEADED_RETRY", "0")
os.environ.setdefault("INSPIRATION_LIVE_CAPTURE_TIMEOUT_S", "6")

CASES: list[dict[str, Any]] = [
	{
		"name": "wide/http_ss_off",
		"query": "b2b product marketing landing",
		"level": "wide",
		"max_ss": 0,
		"live": False,
		"min_hits": 4,
		"timeout": 22,
	},
	{
		"name": "max/http_pack",
		"query": "saas pricing page layout",
		"level": "max",
		"max_ss": 0,
		"live": False,
		"min_hits": 3,
		"timeout": 28,
	},
	{
		"name": "max/live_requested_skip_env",
		"query": "marketing landing hero product",
		"level": "max",
		"max_ss": 1,
		"live": True,
		"skip_browser": True,
		"min_hits": 3,
		"timeout": 28,
	},
	{
		"name": "force_ss_skipped",
		"query": "navbar design examples",
		"level": "standard",
		"max_ss": 1,
		"live": False,
		"allow_browser": True,
		"skip_browser": True,
		"min_hits": 3,
		"timeout": 20,
	},
]


async def run_case(case: dict[str, Any]) -> dict[str, Any]:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	if case.get("skip_browser"):
		os.environ["INSPIRATION_SKIP_LIVE_BROWSER"] = "1"
	else:
		os.environ.pop("INSPIRATION_SKIP_LIVE_BROWSER", None)

	t0 = time.perf_counter()
	try:
		manifest = await asyncio.wait_for(
			collect_inspiration_hits(
				str(case["query"]),
				inspiration_level=str(case["level"]),
				materialize_blobs=False,
				write_per_hit_files=False,
				include_live_sites=bool(case.get("live")),
				include_web_search=True,
				max_web_screenshots=int(case.get("max_ss") or 0),
				allow_browser_screenshot=bool(case.get("allow_browser")),
				use_result_cache=False,
			),
			timeout=float(case.get("timeout") or 30),
		)
	except asyncio.TimeoutError:
		return {
			"name": case["name"],
			"ok": False,
			"wall_s": round(time.perf_counter() - t0, 2),
			"error": "TIMEOUT",
		}
	except Exception as exc:  # noqa: BLE001
		return {
			"name": case["name"],
			"ok": False,
			"wall_s": round(time.perf_counter() - t0, 2),
			"error": f"{type(exc).__name__}: {exc}",
		}

	wall = round(time.perf_counter() - t0, 2)
	hits = list(manifest.get("hits") or [])
	n = int(manifest.get("total_hits") or len(hits))
	ok = n >= int(case.get("min_hits") or 0) and wall <= float(case.get("timeout") or 30)
	ss_hits = sum(
		1
		for h in hits
		if str(h.get("fetch_tier") or "") in {"web_live_screenshot", "live_site"}
		or str(h.get("source_kind") or "") in {"web_live", "famous_site", "live_site"}
	)
	return {
		"name": case["name"],
		"ok": ok,
		"wall_s": wall,
		"hits": n,
		"ss_hits": ss_hits,
		"stop": manifest.get("stop_reason") or "",
		"providers": sorted(
			{str(h.get("provider_id") or "") for h in hits if h.get("provider_id")}
		)[:10],
	}


async def main() -> int:
	print("=" * 72)
	print("LIVE SS / WAF STRESS EVAL (bounded)")
	print("=" * 72)
	rows = []
	for case in CASES:
		print(f"\n>> {case['name']}")
		row = await run_case(case)
		rows.append(row)
		mark = "PASS" if row.get("ok") else "FAIL"
		print(
			f"   [{mark}] wall={row.get('wall_s')}s hits={row.get('hits')} "
			f"ss_hits={row.get('ss_hits')} stop={row.get('stop')!r}"
		)
		if row.get("error"):
			print(f"   ERROR: {row['error']}")

	passed = sum(1 for r in rows if r.get("ok"))
	print("\n" + "=" * 72)
	print(f"SUMMARY  {passed}/{len(rows)} passed")
	print("JSON:" + json.dumps({"passed": passed, "total": len(rows), "cases": rows}, ensure_ascii=True))
	return 0 if passed == len(rows) else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
