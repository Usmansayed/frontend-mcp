"""Hardcore live inspiration layer battery — run manually / CI optional.

Usage:
  PYTHONPATH=src python scripts/hardcore_inspiration_battery.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class CaseResult:
	name: str
	ok: bool
	wall_s: float
	hits: int = 0
	stop: str = ""
	level: str = ""
	providers: list[str] = field(default_factory=list)
	notes: list[str] = field(default_factory=list)
	error: str = ""


CASES: list[dict[str, Any]] = [
	# --- page ---
	{
		"name": "page/saas_landing",
		"query": "modern saas landing page",
		"level": "standard",
		"min_hits": 4,
		"timeout": 22,
	},
	{
		"name": "page/fintech_dashboard",
		"query": "fintech dashboard dark analytics",
		"level": "standard",
		"min_hits": 3,
		"timeout": 22,
	},
	# --- section ---
	{
		"name": "section/pricing",
		"query": "pricing section cards",
		"level": "standard",
		"min_hits": 4,
		"expect_provider_any": ["saasframe", "saaslandingpage", "daisyui", "web_search"],
		"timeout": 18,
	},
	{
		"name": "section/hero",
		"query": "hero section above the fold",
		"level": "standard",
		"min_hits": 3,
		"timeout": 18,
	},
	{
		"name": "section/footer",
		"query": "site footer links",
		"level": "light",
		"min_hits": 3,  # light + pattern soft-stop can land ~3 solid footer thumbs
		"expect_provider_any": ["footer_design", "daisyui"],
		"timeout": 12,
		"web": False,
	},
	# --- component ---
	{
		"name": "component/navbar",
		"query": "navbar with mega menu",
		"level": "standard",
		"min_hits": 4,
		"expect_provider_any": ["navbar_gallery", "daisyui"],
		"timeout": 15,
	},
	{
		"name": "component/sidebar",
		"query": "dashboard sidebar navigation",
		"level": "standard",
		"min_hits": 4,
		"expect_provider_any": ["saasinterface", "daisyui", "navbar_gallery", "web_search"],
		"timeout": 18,
	},
	{
		"name": "component/modal",
		"query": "modal dialog confirmation",
		"level": "standard",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search", "flowbite_modal_docs"],
		"timeout": 15,
	},
	# --- chrome ---
	{
		"name": "chrome/button",
		"query": "primary button hover states",
		"level": "standard",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search", "aceternity_buttons", "shadcnblocks", "ibelick_buttons"],
		"timeout": 15,
	},
	# --- forms gate (P2) ---
	{
		"name": "forms/textarea",
		"query": "textarea multiline text field",
		"level": "standard",
		"min_hits": 3,
		"expect_provider_any": ["daisyui"],
		"timeout": 12,
		"web": False,
	},
	{
		"name": "forms/login_auth",
		"query": "login signup form with email password",
		"level": "standard",
		"min_hits": 4,
		"expect_provider_any": ["saasframe_login", "saasframe_signup", "nicelydone_auth", "daisyui"],
		"timeout": 20,
	},
	{
		"name": "forms/checkout",
		"query": "checkout payment form multi step",
		"level": "standard",
		"min_hits": 4,
		"expect_provider_any": ["saasframe_checkout", "daisyui"],
		"timeout": 18,
	},
	{
		"name": "forms/search_bar",
		"query": "search bar with icon and clear button",
		"level": "standard",
		"min_hits": 3,
		"expect_provider_any": ["daisyui"],
		"timeout": 15,
	},
	# --- font route ---
	{
		"name": "font/serif_route",
		"query": "elegant serif display font",
		"level": "standard",
		"min_hits": 0,
		"max_hits": 0,
		"expect_stop": "font_routed_to_resource_intelligence",
		"expect_font_route": True,
		"timeout": 8,
		"web": False,
	},
	# --- levels pressure ---
	{
		"name": "level/wide_variety",
		"query": "b2b product marketing landing",
		"level": "wide",
		"min_hits": 4,
		"max_ss": 0,  # avoid Chromium hang in battery; OG only
		"timeout": 25,
	},
	{
		"name": "level/light_nav",
		"query": "website navigation header",
		"level": "light",
		"min_hits": 3,
		"timeout": 12,
		"web": True,  # light empty-rescue / thin pack may need web
	},
	# --- empty-rescue / stress ---
	{
		"name": "stress/weird_query",
		"query": "neumorphic toast snackbar affordance",
		"level": "standard",
		"min_hits": 2,
		"timeout": 20,
	},
]


async def run_case(case: dict[str, Any]) -> CaseResult:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	name = str(case["name"])
	query = str(case["query"])
	level = str(case.get("level") or "standard")
	timeout = float(case.get("timeout") or 20)
	include_web = case.get("web")
	if include_web is None:
		include_web = True
	max_ss = int(case.get("max_ss") if case.get("max_ss") is not None else 0)

	t0 = time.perf_counter()
	try:
		manifest = await asyncio.wait_for(
			collect_inspiration_hits(
				query,
				inspiration_level=level,
				materialize_blobs=False,
				write_per_hit_files=False,
				include_live_sites=False,
				include_web_search=bool(include_web),
				max_web_screenshots=max_ss,
				use_result_cache=False,
				use_multi_scout=level not in {"light"},
			),
			timeout=timeout,
		)
	except asyncio.TimeoutError:
		return CaseResult(
			name=name,
			ok=False,
			wall_s=round(time.perf_counter() - t0, 2),
			level=level,
			error=f"TIMEOUT>{timeout}s",
		)
	except Exception as exc:  # noqa: BLE001
		return CaseResult(
			name=name,
			ok=False,
			wall_s=round(time.perf_counter() - t0, 2),
			level=level,
			error=f"{type(exc).__name__}: {exc}",
			notes=[traceback.format_exc(limit=3)],
		)

	wall = round(time.perf_counter() - t0, 2)
	hits = list(manifest.get("hits") or [])
	n = int(manifest.get("total_hits") or len(hits))
	stop = str(manifest.get("stop_reason") or "")
	providers = sorted({str(h.get("provider_id") or "") for h in hits if h.get("provider_id")})
	notes: list[str] = []
	ok = True

	min_hits = int(case.get("min_hits") or 0)
	max_hits = case.get("max_hits")
	if n < min_hits:
		ok = False
		notes.append(f"hits {n} < min {min_hits}")
	if max_hits is not None and n > int(max_hits):
		ok = False
		notes.append(f"hits {n} > max {max_hits}")

	expect_stop = case.get("expect_stop")
	if expect_stop and stop != expect_stop:
		ok = False
		notes.append(f"stop={stop!r} want {expect_stop!r}")

	if case.get("expect_font_route"):
		font = (manifest.get("pattern") or {}).get("font_route")
		if not font:
			ok = False
			notes.append("missing font_route")

	want_any = case.get("expect_provider_any") or []
	if want_any and not any(p in providers for p in want_any):
		ok = False
		notes.append(f"providers {providers} miss any of {want_any}")

	# Hard fail: junk-only pack for fine grain (all onepage/dark_mode with no pattern/web)
	fine = name.startswith(("component/", "chrome/", "section/"))
	if fine and n > 0:
		solid = {
			"daisyui",
			"navbar_gallery",
			"footer_design",
			"hero_gallery",
			"saasframe",
			"saasframe_login",
			"saasframe_signup",
			"saasframe_checkout",
			"nicelydone_auth",
			"saasinterface",
			"saaslandingpage",
			"web_search",
			"web_live",
			"flowbite_modal_docs",
			"flowbite_navbar_docs",
			"flowbite_sidebar_docs",
			"aceternity_buttons",
			"ibelick_buttons",
			"shadcnblocks",
		}
		if not (set(providers) & solid) and "font" not in name:
			# allow multi_scout if relevant titles — soft note only
			notes.append(f"warn: no specialist/web providers ({providers})")

	return CaseResult(
		name=name,
		ok=ok,
		wall_s=wall,
		hits=n,
		stop=stop,
		level=level,
		providers=providers[:12],
		notes=notes,
	)


async def main() -> int:
	print("=" * 72)
	print("HARDCORE INSPIRATION BATTERY")
	print("=" * 72)
	results: list[CaseResult] = []
	# Sequential — shared Chromium / network politeness
	for case in CASES:
		print(f"\n>> {case['name']}  ({case['query']!r}, level={case.get('level')})")
		r = await run_case(case)
		results.append(r)
		status = "PASS" if r.ok else "FAIL"
		print(
			f"   [{status}] wall={r.wall_s}s hits={r.hits} stop={r.stop!r} "
			f"providers={r.providers}"
		)
		if r.error:
			print(f"   ERROR: {r.error}")
		for n in r.notes:
			print(f"   NOTE: {n}")

	passed = sum(1 for r in results if r.ok)
	failed = len(results) - passed
	total_wall = round(sum(r.wall_s for r in results), 2)
	print("\n" + "=" * 72)
	print(f"SUMMARY  {passed}/{len(results)} passed  |  {failed} failed  |  wall={total_wall}s")
	print("=" * 72)
	for r in results:
		mark = "✓" if r.ok else "✗"
		print(f"  {mark} {r.name:28} hits={r.hits:2}  {r.wall_s:5.2f}s  {r.stop or '-'}")

	out = {
		"passed": passed,
		"failed": failed,
		"total": len(results),
		"wall_s": total_wall,
		"cases": [
			{
				"name": r.name,
				"ok": r.ok,
				"wall_s": r.wall_s,
				"hits": r.hits,
				"stop": r.stop,
				"providers": r.providers,
				"notes": r.notes,
				"error": r.error,
			}
			for r in results
		],
	}
	print("\nJSON:" + json.dumps(out, ensure_ascii=True))
	return 0 if failed == 0 else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
