"""Fair Scrapling vs our http_get battery (session-aware).

First spike used cold ``Fetcher.get`` (temporary session per URL) — Scrapling
docs say that is ~10× slower than ``FetcherSession``. This script compares:

  ours              — httpx keep-alive pool (default inspiration path)
  scrapling_cold    — Fetcher.get (unfair / what we did before)
  scrapling_session — process-wide FetcherSession (proper usage)
  scrapling_async   — async FetcherSession gather (proper concurrent)
  hybrid            — ours first; Scrapling session on 403/block

Also runs integrated collect A/B (default vs scrapling vs hybrid) on a few
queries so system-level fairness is measured, not just raw GET latency.

Usage:
  PYTHONPATH=src python scripts/eval_scrapling_vs_http.py
  PYTHONPATH=src python scripts/eval_scrapling_vs_http.py --skip-collect
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

TARGETS: list[dict[str, str]] = [
	{"id": "saasframe_login", "url": "https://www.saasframe.io/categories/login"},
	{"id": "saasframe_checkout", "url": "https://www.saasframe.io/categories/checkout"},
	{"id": "navbar_gallery", "url": "https://www.navbar.gallery/"},
	{"id": "footer_design", "url": "https://www.footer.design/"},
	{"id": "onepagelove", "url": "https://onepagelove.com/inspiration?s=login"},
	{"id": "httpster", "url": "https://httpster.net/"},
	{"id": "lapa", "url": "https://www.lapa.ninja/?s=saas"},
	{"id": "nicelydone_auth", "url": "https://nicelydone.club/tags/authentication"},
	{"id": "daisy_input", "url": "https://img.daisyui.com/images/components/input.webp"},
	{"id": "ddg_html", "url": "https://html.duckduckgo.com/html/?q=login+form+ui+design"},
	{"id": "behance", "url": "https://www.behance.net/search/projects?search=login+form"},
	{"id": "landbook", "url": "https://land-book.com/design?search=saas"},
]

ROUNDS = 2
TIMEOUT_S = 8.0
MAX_BYTES = 120_000
BURST_N = 8
COLLECT_QUERIES = [
	"login form saas",
	"checkout form",
	"pricing page saas",
]


@dataclass
class Row:
	engine: str
	target: str
	ok: bool
	status: int | None
	wall_ms: float
	bytes: int = 0
	previews: int = 0
	error: str = ""
	notes: list[str] = field(default_factory=list)


def _previews(html: str) -> int:
	from navigation.inspiration_intelligence.pattern_acquire import extract_pattern_previews

	return len(extract_pattern_previews(html or "", extract="any_img", limit=8))


def _body_from_page(page: Any) -> tuple[str, int | None]:
	status = getattr(page, "status", None) or getattr(page, "status_code", None)
	body = ""
	for attr in ("html", "body", "text", "content"):
		val = getattr(page, attr, None)
		if val is None:
			continue
		if isinstance(val, (bytes, bytearray)):
			body = bytes(val).decode("utf-8", errors="replace")
		else:
			body = str(val)
		if body:
			break
	if MAX_BYTES and len(body) > MAX_BYTES:
		body = body[:MAX_BYTES]
	return body, int(status) if status is not None else None


def fetch_ours(url: str) -> tuple[str, int | None, str | None, float]:
	# Force default path (ignore ambient INSPIRATION_HTTP_BACKEND)
	prev = os.environ.pop("INSPIRATION_HTTP_BACKEND", None)
	try:
		from navigation.inspiration_intelligence.browser.fetch import http_get

		t0 = time.perf_counter()
		body, status, err = http_get(url, timeout=TIMEOUT_S, max_bytes=MAX_BYTES)
		return body or "", status, err, (time.perf_counter() - t0) * 1000.0
	finally:
		if prev is not None:
			os.environ["INSPIRATION_HTTP_BACKEND"] = prev


def fetch_scrapling_cold(url: str) -> tuple[str, int | None, str | None, float]:
	from scrapling.fetchers import Fetcher

	t0 = time.perf_counter()
	try:
		page = Fetcher.get(url, timeout=TIMEOUT_S, impersonate="chrome", retries=1, retry_delay=0)
		body, status = _body_from_page(page)
		err = f"http_{status}" if status and status >= 400 and not body else None
		return body, status, err, (time.perf_counter() - t0) * 1000.0
	except Exception as exc:  # noqa: BLE001
		return "", None, f"{type(exc).__name__}:{exc}", (time.perf_counter() - t0) * 1000.0


def fetch_scrapling_session(url: str) -> tuple[str, int | None, str | None, float]:
	from navigation.inspiration_intelligence.browser.scrapling_pool import session_get

	t0 = time.perf_counter()
	got = session_get(url, timeout=TIMEOUT_S, max_bytes=MAX_BYTES)
	wall = (time.perf_counter() - t0) * 1000.0
	if got is None:
		return "", None, "session_unavailable", wall
	body, status, err = got
	return body or "", status, err, wall


def fetch_hybrid(url: str) -> tuple[str, int | None, str | None, float]:
	"""ours first; Scrapling session on 403/block — mirrors scrapling_fallback."""
	from navigation.inspiration_intelligence.browser.fetch import _should_scrapling_retry
	from navigation.inspiration_intelligence.browser.scrapling_pool import session_get

	t0 = time.perf_counter()
	body, status, err = fetch_ours(url)[:3]
	if _should_scrapling_retry(status, err, body or ""):
		got = session_get(url, timeout=TIMEOUT_S, max_bytes=MAX_BYTES)
		if got is not None:
			b2, st2, e2 = got
			if b2 and (st2 is None or st2 < 400):
				return b2, st2, e2, (time.perf_counter() - t0) * 1000.0
	return body or "", status, err, (time.perf_counter() - t0) * 1000.0


def score_row(engine: str, target: str, body: str, status: int | None, err: str | None, wall: float) -> Row:
	ok = bool(body) and (status is None or status < 400) and not (err and not body)
	if target.startswith("daisy_") and status and status < 400:
		ok = True
	previews = 0
	if body and not target.startswith("daisy_"):
		try:
			previews = _previews(body)
		except Exception:
			previews = 0
	return Row(
		engine=engine,
		target=target,
		ok=ok,
		status=status,
		wall_ms=round(wall, 1),
		bytes=len(body or ""),
		previews=previews,
		error=(err or "")[:160],
	)


def concurrent_burst_threads(engine: str, urls: list[str], n: int = BURST_N) -> dict[str, Any]:
	"""Thread fan-out — matches inspiration scout (ThreadPool), not asyncio gather."""
	sample = (urls * ((n // len(urls)) + 1))[:n]
	fn = {
		"ours": fetch_ours,
		"scrapling_cold": fetch_scrapling_cold,
		"scrapling_session": fetch_scrapling_session,
		"hybrid": fetch_hybrid,
	}[engine]
	t0 = time.perf_counter()
	oks = 0
	with ThreadPoolExecutor(max_workers=n) as pool:
		futs = [pool.submit(fn, u) for u in sample]
		for fut in as_completed(futs):
			try:
				body, status, err, _ = fut.result()
				if body and (status is None or status < 400):
					oks += 1
			except Exception:
				pass
	return {"engine": engine, "n": n, "ok": oks, "wall_ms": round((time.perf_counter() - t0) * 1000.0, 1)}


async def concurrent_burst_async_session(urls: list[str], n: int = BURST_N) -> dict[str, Any]:
	"""Proper Scrapling concurrent pattern: async with FetcherSession + gather."""
	from scrapling.fetchers import FetcherSession

	sample = (urls * ((n // len(urls)) + 1))[:n]
	t0 = time.perf_counter()
	oks = 0
	try:
		async with FetcherSession(
			impersonate="chrome",
			stealthy_headers=True,
			timeout=TIMEOUT_S,
			retries=1,
			retry_delay=0,
		) as session:
			pages = await asyncio.gather(
				*[session.get(u) for u in sample],
				return_exceptions=True,
			)
		for page in pages:
			if isinstance(page, Exception):
				continue
			body, status = _body_from_page(page)
			if body and (status is None or status < 400):
				oks += 1
	except Exception as exc:  # noqa: BLE001
		return {
			"engine": "scrapling_async_session",
			"n": n,
			"ok": 0,
			"wall_ms": round((time.perf_counter() - t0) * 1000.0, 1),
			"error": str(exc)[:160],
		}
	return {
		"engine": "scrapling_async_session",
		"n": n,
		"ok": oks,
		"wall_ms": round((time.perf_counter() - t0) * 1000.0, 1),
	}


def summarize(rows: list[Row], engine: str) -> dict[str, Any]:
	subset = [r for r in rows if r.engine == engine]
	by_t: dict[str, list[Row]] = {}
	for r in subset:
		by_t.setdefault(r.target, []).append(r)
	best = [min(v, key=lambda x: (not x.ok, x.wall_ms)) for v in by_t.values()]
	ok_n = sum(1 for r in best if r.ok)
	lat = [r.wall_ms for r in best if r.ok]
	return {
		"engine": engine,
		"targets_ok": ok_n,
		"targets_total": len(best),
		"ok_rate": round(ok_n / max(1, len(best)), 3),
		"p50_ms": round(statistics.median(lat), 1) if lat else None,
		"p95_ms": round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)], 1) if lat else None,
		"mean_ms": round(statistics.mean(lat), 1) if lat else None,
		"failed": [r.target for r in best if not r.ok],
	}


def run_http_battery() -> tuple[list[Row], list[dict[str, Any]]]:
	engines = [
		("ours", fetch_ours),
		("scrapling_cold", fetch_scrapling_cold),
		("scrapling_session", fetch_scrapling_session),
		("hybrid", fetch_hybrid),
	]
	rows: list[Row] = []
	for target in TARGETS:
		tid, url = target["id"], target["url"]
		print(f"\n>> {tid}")
		for round_i in range(ROUNDS):
			for name, fn in engines:
				b, st, err, ms = fn(url)
				r = score_row(name, tid, b, st, err, ms)
				rows.append(r)
				print(
					f"   {name:18s} r{round_i+1} ok={r.ok} status={r.status} "
					f"{r.wall_ms:7.1f}ms bytes={r.bytes} previews={r.previews} {r.error}"
				)

	burst_urls = [
		"https://www.saasframe.io/categories/login",
		"https://www.navbar.gallery/",
		"https://www.footer.design/",
		"https://httpster.net/",
	]
	print(f"\n>> concurrent thread burst n={BURST_N}")
	bursts: list[dict[str, Any]] = []
	for name in ("ours", "scrapling_cold", "scrapling_session", "hybrid"):
		b = concurrent_burst_threads(name, burst_urls, BURST_N)
		bursts.append(b)
		print(f"   {b}")
	print("\n>> concurrent async FetcherSession gather")
	ab = asyncio.run(concurrent_burst_async_session(burst_urls, BURST_N))
	bursts.append(ab)
	print(f"   {ab}")
	return rows, bursts


def run_collect_ab() -> list[dict[str, Any]]:
	"""System-level: same collect path, three backends."""

	async def _one(query: str, level: str = "light") -> dict[str, Any]:
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
					include_web_search=True,
					max_web_screenshots=0,
					use_result_cache=False,
					use_multi_scout=False,
				),
				timeout=25.0,
			)
			hits = list(manifest.get("hits") or [])
			n = int(manifest.get("total_hits") or len(hits))
			providers = sorted(
				{str(h.get("provider_id") or "") for h in hits if h.get("provider_id")}
			)
			return {
				"hits": n,
				"wall_ms": round((time.perf_counter() - t0) * 1000.0, 1),
				"providers": providers[:12],
				"ok": n >= 3,
				"stop": str(manifest.get("stop_reason") or ""),
			}
		except Exception as exc:  # noqa: BLE001
			return {
				"hits": 0,
				"wall_ms": round((time.perf_counter() - t0) * 1000.0, 1),
				"providers": [],
				"ok": False,
				"error": f"{type(exc).__name__}:{exc}"[:200],
			}

	results: list[dict[str, Any]] = []
	backends = [
		("ours", ""),
		("scrapling", "scrapling"),
		("hybrid", "scrapling_fallback"),
	]
	prev = os.environ.get("INSPIRATION_HTTP_BACKEND")
	try:
		for label, env_val in backends:
			if env_val:
				os.environ["INSPIRATION_HTTP_BACKEND"] = env_val
			else:
				os.environ.pop("INSPIRATION_HTTP_BACKEND", None)
			# Reset pools so backend switch is clean
			from navigation.inspiration_intelligence.browser.scrapling_pool import (
				close_shared_scrapling_session,
			)

			close_shared_scrapling_session()
			for q in COLLECT_QUERIES:
				print(f"\n>> collect [{label}] {q!r}")
				row = asyncio.run(_one(q))
				row["backend"] = label
				row["query"] = q
				results.append(row)
				print(
					f"   hits={row['hits']} wall={row['wall_ms']}ms "
					f"providers={row.get('providers')} ok={row['ok']} {row.get('error', '')}"
				)
	finally:
		if prev is None:
			os.environ.pop("INSPIRATION_HTTP_BACKEND", None)
		else:
			os.environ["INSPIRATION_HTTP_BACKEND"] = prev
	return results


def pick_verdict(summaries: dict[str, dict[str, Any]], bursts: list[dict[str, Any]]) -> str:
	ours = summaries.get("ours") or {}
	sess = summaries.get("scrapling_session") or {}
	cold = summaries.get("scrapling_cold") or {}
	hybrid = summaries.get("hybrid") or {}
	# Prefer reliability, then session speed vs ours
	if (hybrid.get("ok_rate") or 0) > (ours.get("ok_rate") or 0) + 0.04:
		return "hybrid_best_reliability"
	if (sess.get("ok_rate") or 0) > (ours.get("ok_rate") or 0) + 0.04:
		return "scrapling_session_more_reliable"
	# Session should crush cold — if not, integration bug
	if (sess.get("p50_ms") or 9e9) < (cold.get("p50_ms") or 9e9) * 0.5:
		session_fixed = True
	else:
		session_fixed = False
	burst_ours = next((b for b in bursts if b.get("engine") == "ours"), {})
	burst_sess = next((b for b in bursts if b.get("engine") == "scrapling_session"), {})
	if (burst_sess.get("wall_ms") or 9e9) < (burst_ours.get("wall_ms") or 9e9) * 0.85:
		return "scrapling_session_faster_burst" + ("_and_cold_was_unfair" if session_fixed else "")
	if (ours.get("p50_ms") or 9e9) < (sess.get("p50_ms") or 9e9) * 0.85:
		return "ours_still_faster_with_fair_session" + ("_cold_was_unfair" if session_fixed else "")
	if session_fixed:
		return "fair_tie_session_much_faster_than_cold"
	return "tie"


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--skip-collect", action="store_true")
	args = parser.parse_args()

	print("=" * 72)
	print("FAIR Scrapling vs http_get — session + cold + hybrid + collect")
	print("=" * 72)
	try:
		from scrapling.fetchers import Fetcher, FetcherSession  # noqa: F401
	except ImportError as exc:
		print("Scrapling not installed:", exc)
		print('  pip install "scrapling[fetchers]"')
		return 2

	# Reset scrapling pool between runs
	from navigation.inspiration_intelligence.browser.scrapling_pool import close_shared_scrapling_session

	close_shared_scrapling_session()

	rows, bursts = run_http_battery()
	engines = ("ours", "scrapling_cold", "scrapling_session", "hybrid")
	summaries = {e: summarize(rows, e) for e in engines}

	print("\n" + "=" * 72)
	print("HTTP SUMMARY")
	print("=" * 72)
	for e in engines:
		print(e, json.dumps(summaries[e]))
	print("bursts", json.dumps(bursts))

	collect_rows: list[dict[str, Any]] = []
	if not args.skip_collect:
		print("\n" + "=" * 72)
		print("INTEGRATED COLLECT A/B")
		print("=" * 72)
		collect_rows = run_collect_ab()

	verdict = pick_verdict(summaries, bursts)
	out = {
		"verdict": verdict,
		"summaries": summaries,
		"bursts": bursts,
		"collect": collect_rows,
		"rows": [asdict(r) for r in rows],
		"methodology": {
			"cold": "Fetcher.get — temporary session per request (docs: ~10x slower)",
			"session": "process-wide FetcherSession (fair vs httpx pool)",
			"hybrid": "httpx first; Scrapling session on 403/block",
			"burst": "ThreadPool n=8 matches inspiration scout fan-out",
			"async_burst": "async with FetcherSession + gather (Scrapling recommended)",
			"retries": "Scrapling retries=1 retry_delay=0 (not default 3×1s)",
		},
	}
	print("\nVERDICT:", verdict)
	report = Path("docs/research/scrapling_spike_results.json")
	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text(json.dumps(out, indent=2), encoding="utf-8")
	print(f"Wrote {report}")
	close_shared_scrapling_session()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
