"""Live battery: forms, text inputs, auth/checkout sections, and related pages.

Usage:
  PYTHONPATH=src python scripts/eval_inspiration_forms_sections.py
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
	scope: str = ""
	providers: list[str] = field(default_factory=list)
	notes: list[str] = field(default_factory=list)
	error: str = ""


# Plan: cover chrome (controls), component (composite), section (blocks), page (surfaces)
CASES: list[dict[str, Any]] = [
	# --- chrome: text / form controls ---
	{
		"name": "chrome/text_input",
		"query": "text input with label and placeholder",
		"level": "standard",
		"expect_scope": "chrome",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search"],
		"timeout": 15,
	},
	{
		"name": "chrome/checkbox_toggle",
		"query": "checkbox toggle switch ui",
		"level": "standard",
		"expect_scope": "chrome",
		"min_hits": 3,
		"expect_provider_any": ["daisyui"],
		"timeout": 12,
		"web": False,
	},
	{
		"name": "chrome/textarea",
		"query": "textarea multiline text field",
		"level": "standard",
		"expect_scope": "chrome",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search"],
		"timeout": 15,
	},
	# --- component: composite inputs ---
	{
		"name": "component/search_bar",
		"query": "search bar with icon and clear button",
		"level": "standard",
		"expect_scope": "component",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search", "navbar_gallery"],
		"timeout": 18,
	},
	{
		"name": "component/dropdown_select",
		"query": "dropdown select combobox menu",
		"level": "standard",
		"expect_scope": "component",
		"min_hits": 3,
		"expect_provider_any": ["daisyui", "web_search"],
		"timeout": 15,
	},
	# --- section: form blocks ---
	{
		"name": "section/login_auth",
		"query": "login signup form with email password",
		"level": "standard",
		"expect_scope": "section",
		"expect_intent": "auth",
		"min_hits": 3,
		"expect_provider_any": ["web_search", "daisyui", "saasframe_login", "saasframe_signup", "nicelydone_auth", "onepagelove"],
		"timeout": 20,
	},
	{
		"name": "section/checkout",
		"query": "checkout payment form multi step",
		"level": "standard",
		"expect_scope": "section",
		"expect_intent": "checkout",
		"min_hits": 3,
		"expect_provider_any": ["web_search", "daisyui", "saasframe_checkout", "saasframe", "onepagelove"],
		"timeout": 20,
	},
	{
		"name": "section/contact_form",
		"query": "contact form section name email message",
		"level": "standard",
		"min_hits": 2,
		"expect_provider_any": ["daisyui", "web_search", "saasframe_signup", "nicelydone_auth"],
		"timeout": 18,
	},
	# --- page: full surfaces with forms ---
	{
		"name": "page/signup_onboarding",
		"query": "signup registration onboarding page",
		"level": "standard",
		"min_hits": 3,
		"expect_provider_any": ["web_search", "onepagelove", "saasframe_signup", "saaslandingpage", "daisyui", "nicelydone_auth"],
		"timeout": 22,
	},
	{
		"name": "page/settings_profile",
		"query": "user settings profile form page",
		"level": "standard",
		"min_hits": 2,
		"expect_provider_any": ["daisyui", "web_search", "saasinterface", "onepagelove", "saas_landing_page", "httpster"],
		"timeout": 20,
	},
	{
		"name": "page/saas_landing_cta",
		"query": "saas landing page email capture form",
		"level": "standard",
		"expect_scope": "page",
		"min_hits": 4,
		"expect_provider_any": ["web_search", "saas_landing_page", "onepagelove", "daisyui"],
		"timeout": 22,
	},
]


async def run_case(case: dict[str, Any]) -> CaseResult:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.query_flex import resolve_flexible_query

	name = str(case["name"])
	query = str(case["query"])
	level = str(case.get("level") or "standard")
	timeout = float(case.get("timeout") or 20)
	include_web = case.get("web")
	if include_web is None:
		include_web = True

	flex = resolve_flexible_query(query)
	scope = flex.scope

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
				max_web_screenshots=0,
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
			scope=scope,
			error=f"TIMEOUT>{timeout}s",
		)
	except Exception as exc:  # noqa: BLE001
		return CaseResult(
			name=name,
			ok=False,
			wall_s=round(time.perf_counter() - t0, 2),
			scope=scope,
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

	expect_scope = case.get("expect_scope")
	if expect_scope and scope != expect_scope:
		ok = False
		notes.append(f"scope={scope!r} want {expect_scope!r}")

	expect_intent = case.get("expect_intent")
	if expect_intent and flex.intent_class != expect_intent:
		ok = False
		notes.append(f"intent={flex.intent_class!r} want {expect_intent!r}")

	min_hits = int(case.get("min_hits") or 0)
	if n < min_hits:
		ok = False
		notes.append(f"hits {n} < min {min_hits}")

	want_any = case.get("expect_provider_any") or []
	if want_any and not any(p in providers for p in want_any):
		ok = False
		notes.append(f"providers {providers} miss any of {want_any}")

	# Soft diagnostic: daisy slug coverage for chrome input asks
	if name.startswith("chrome/") and "daisyui" not in providers and n > 0:
		notes.append("warn: no daisyui chrome preview")

	return CaseResult(
		name=name,
		ok=ok,
		wall_s=wall,
		hits=n,
		stop=stop,
		scope=scope,
		providers=providers[:12],
		notes=notes,
	)


async def main() -> int:
	print("=" * 72)
	print("FORMS / INPUTS / SECTIONS INSPIRATION BATTERY")
	print("=" * 72)
	results: list[CaseResult] = []
	for case in CASES:
		print(f"\n>> {case['name']}  ({case['query']!r}, level={case.get('level')})")
		r = await run_case(case)
		results.append(r)
		status = "PASS" if r.ok else "FAIL"
		print(
			f"   [{status}] scope={r.scope} wall={r.wall_s}s hits={r.hits} "
			f"stop={r.stop!r} providers={r.providers}"
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
		print(f"  {mark} {r.name:28} scope={r.scope:9} hits={r.hits:2}  {r.wall_s:5.2f}s")

	out = {
		"passed": passed,
		"failed": failed,
		"total": len(results),
		"wall_s": total_wall,
		"cases": [
			{
				"name": r.name,
				"ok": r.ok,
				"scope": r.scope,
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
