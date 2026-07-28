"""Hard-target bake-off: Scrapling StealthySession vs our Chromium (lean).

People calling Scrapling powerful usually mean StealthyFetcher / CF bypass —
not HTTP FetcherSession. This script measures that claim fairly.

Engines (per URL):
  http_ours        — httpx pool
  http_scrapling   — FetcherSession (TLS only)
  chromium_ours    — InspirationBrowserSession.fetch_html
  stealthy_cf      — one StealthySession (solve_cloudflare=True) reused

Usage:
  PYTHONPATH=src python -u scripts/eval_scrapling_stealthy_vs_chromium.py
"""
from __future__ import annotations

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
sys.stderr.reconfigure(encoding="utf-8")

TARGETS: list[dict[str, str]] = [
	{"id": "behance", "url": "https://www.behance.net/search/projects?search=login+form"},
	{"id": "landbook", "url": "https://land-book.com/"},
	{"id": "lapa", "url": "https://www.lapa.ninja/?s=saas"},
	{"id": "dribbble", "url": "https://dribbble.com/search/shots/recent?q=login+form"},
]

TIMEOUT_HTTP_S = 10.0
TIMEOUT_BROWSER_MS = 35_000
MAX_HTML = 180_000


@dataclass
class Row:
	engine: str
	target: str
	ok: bool
	status: int | None
	wall_ms: float
	bytes: int = 0
	previews: int = 0
	block: str = ""
	error: str = ""
	notes: list[str] = field(default_factory=list)


def log(msg: str) -> None:
	print(msg, flush=True)


def _previews(html: str) -> int:
	from navigation.inspiration_intelligence.pattern_acquire import extract_pattern_previews

	return len(extract_pattern_previews(html or "", extract="any_img", limit=8))


def _block(html: str, status: int | None) -> str:
	from navigation.inspiration_intelligence.browser.policy import detect_block_signal

	return detect_block_signal(html or "", status_code=status) or ""


def _score(
	engine: str,
	target: str,
	body: str,
	status: int | None,
	err: str | None,
	wall: float,
	notes: list[str] | None = None,
) -> Row:
	block = _block(body, status) if (body or status is not None) else ""
	previews = 0
	if body:
		try:
			previews = _previews(body)
		except Exception:
			previews = 0
	hard_block = block in {
		"bot_challenge_detected",
		"waf_stub_page",
		"http_403",
		"http_429",
		"http_503",
		"http_202",
	}
	ok = bool(body) and not hard_block and (status is None or status < 400)
	if previews >= 3:
		ok = True
		block = ""
	if err and not body:
		ok = False
	return Row(
		engine=engine,
		target=target,
		ok=ok,
		status=status,
		wall_ms=round(wall, 1),
		bytes=len(body or ""),
		previews=previews,
		block=block,
		error=(err or "")[:200],
		notes=list(notes or [])[:8],
	)


def _body_from_page(page: Any) -> tuple[str, int | None]:
	status = getattr(page, "status", None) or getattr(page, "status_code", None)
	body = ""
	# Stealthy Response: html_content (str) / body (bytes) — not .html
	for attr in ("html_content", "html", "body", "text", "content"):
		val = getattr(page, attr, None)
		if val is None:
			continue
		if isinstance(val, (bytes, bytearray)):
			body = bytes(val).decode("utf-8", errors="replace")
		else:
			body = str(val)
		if body:
			break
	if len(body) > MAX_HTML:
		body = body[:MAX_HTML]
	return body, int(status) if status is not None else None


def fetch_http_ours(url: str) -> tuple[str, int | None, str | None, float]:
	prev = os.environ.pop("INSPIRATION_HTTP_BACKEND", None)
	try:
		from navigation.inspiration_intelligence.browser.fetch import http_get

		t0 = time.perf_counter()
		body, status, err = http_get(url, timeout=TIMEOUT_HTTP_S, max_bytes=MAX_HTML)
		return body or "", status, err, (time.perf_counter() - t0) * 1000.0
	finally:
		if prev is not None:
			os.environ["INSPIRATION_HTTP_BACKEND"] = prev


def fetch_http_scrapling(url: str) -> tuple[str, int | None, str | None, float]:
	from navigation.inspiration_intelligence.browser.scrapling_pool import session_get

	t0 = time.perf_counter()
	got = session_get(url, timeout=TIMEOUT_HTTP_S, max_bytes=MAX_HTML)
	wall = (time.perf_counter() - t0) * 1000.0
	if got is None:
		return "", None, "session_unavailable", wall
	body, status, err = got
	return body or "", status, err, wall


async def fetch_chromium_one(url: str, target_id: str) -> tuple[str, int | None, str | None, float, list[str]]:
	from navigation.inspiration_intelligence.browser.policy import ProviderFetchPolicy
	from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

	notes: list[str] = []
	t0 = time.perf_counter()
	policy = ProviderFetchPolicy(
		provider_id=target_id,
		hydration_wait_s=2.0,
		min_delay_s=0.1,
		max_delay_s=0.2,
	)
	session: InspirationBrowserSession | None = None
	try:
		session = InspirationBrowserSession(
			provider_id=target_id,
			policy=policy,
			headless=True,
			base_url=url,
		)
		await asyncio.wait_for(session.start(), timeout=40.0)
		html, deg = await asyncio.wait_for(session.fetch_html(url), timeout=50.0)
		notes.extend(deg or [])
		body = (html or "")[:MAX_HTML]
		wall = (time.perf_counter() - t0) * 1000.0
		status = 200 if body else None
		err = "chromium_block" if any("block" in d for d in notes) and len(body) < 3000 else None
		return body, status, err, wall, notes
	except Exception as exc:  # noqa: BLE001
		return "", None, f"{type(exc).__name__}:{exc}", (time.perf_counter() - t0) * 1000.0, notes
	finally:
		if session is not None:
			try:
				if session._runtime:  # noqa: SLF001
					await session._runtime.force_kill()  # noqa: SLF001
				else:
					await session.close()
			except Exception:
				pass


def summarize(rows: list[Row], engine: str) -> dict[str, Any]:
	subset = [r for r in rows if r.engine == engine]
	ok_n = sum(1 for r in subset if r.ok)
	lat = [r.wall_ms for r in subset if r.ok]
	prev = [r.previews for r in subset if r.ok]
	ours_fail = {r.target for r in rows if r.engine == "http_ours" and not r.ok}
	return {
		"engine": engine,
		"targets_ok": ok_n,
		"targets_total": len(subset),
		"ok_rate": round(ok_n / max(1, len(subset)), 3),
		"p50_ms": round(statistics.median(lat), 1) if lat else None,
		"mean_ms": round(statistics.mean(lat), 1) if lat else None,
		"mean_previews_ok": round(statistics.mean(prev), 2) if prev else 0,
		"failed": [r.target for r in subset if not r.ok],
		"unlocked_vs_http_ours": sorted(
			r.target for r in subset if r.ok and r.target in ours_fail
		),
	}


async def main_async() -> int:
	log("=" * 72)
	log("STEALTHY vs CHROMIUM — hard hosts (lean / session-reuse)")
	log("=" * 72)
	try:
		from scrapling.fetchers import AsyncStealthySession  # noqa: F401
	except ImportError as exc:
		log(f"Scrapling missing: {exc}")
		return 2

	rows: list[Row] = []

	# --- Phase 1: HTTP baselines (fast) ---
	log("\n== Phase 1: HTTP ==")
	for target in TARGETS:
		tid, url = target["id"], target["url"]
		log(f"\n>> {tid}")
		for name, fn in (("http_ours", fetch_http_ours), ("http_scrapling", fetch_http_scrapling)):
			b, st, err, ms = fn(url)
			r = _score(name, tid, b, st, err, ms)
			rows.append(r)
			log(f"   {name:16s} ok={r.ok} st={r.status} {r.wall_ms:7.0f}ms prev={r.previews} block={r.block!r} {r.error}")

	# --- Phase 2: our Chromium (one target at a time, force_kill) ---
	log("\n== Phase 2: chromium_ours ==")
	for target in TARGETS:
		tid, url = target["id"], target["url"]
		log(f"\n>> chromium {tid}")
		b, st, err, ms, notes = await fetch_chromium_one(url, tid)
		r = _score("chromium_ours", tid, b, st, err, ms, notes)
		rows.append(r)
		log(f"   chromium_ours    ok={r.ok} st={r.status} {r.wall_ms:7.0f}ms prev={r.previews} block={r.block!r} notes={notes[:3]} {r.error}")

	# --- Phase 3: AsyncStealthySession (must be async inside our event loop) ---
	log("\n== Phase 3: stealthy_cf (AsyncStealthySession reused) ==")
	try:
		from scrapling.fetchers import AsyncStealthySession

		async with AsyncStealthySession(
			headless=True,
			timeout=TIMEOUT_BROWSER_MS,
			network_idle=True,
			solve_cloudflare=True,
			retries=1,
			retry_delay=0,
		) as session:
			for target in TARGETS:
				tid, url = target["id"], target["url"]
				log(f"\n>> stealthy {tid}")
				t0 = time.perf_counter()
				try:
					page = await session.fetch(url)
					body, status = _body_from_page(page)
					err = None
					if status and status >= 400 and not body:
						err = f"http_{status}"
					wall = (time.perf_counter() - t0) * 1000.0
					r = _score(
						"stealthy_cf",
						tid,
						body,
						status,
						err,
						wall,
						["solve_cf=True", "async_session_reuse"],
					)
				except Exception as exc:  # noqa: BLE001
					wall = (time.perf_counter() - t0) * 1000.0
					r = _score("stealthy_cf", tid, "", None, f"{type(exc).__name__}:{exc}", wall)
				rows.append(r)
				log(
					f"   stealthy_cf      ok={r.ok} st={r.status} {r.wall_ms:7.0f}ms "
					f"prev={r.previews} block={r.block!r} {r.error}"
				)
	except Exception as exc:  # noqa: BLE001
		log(f"AsyncStealthySession failed: {type(exc).__name__}: {exc}")
		for target in TARGETS:
			rows.append(_score("stealthy_cf", target["id"], "", None, f"session_start:{exc}", 0.0))

	engines = ["http_ours", "http_scrapling", "chromium_ours", "stealthy_cf"]
	summaries = {e: summarize(rows, e) for e in engines}

	log("\n" + "=" * 72)
	log("SUMMARY")
	log("=" * 72)
	for e in engines:
		log(f"{e}: {json.dumps(summaries[e])}")

	sc = summaries["stealthy_cf"]
	cr = summaries["chromium_ours"]
	hs = summaries["http_scrapling"]
	stealthy_ran = not all(
		(r.error or "").startswith("session_start:") for r in rows if r.engine == "stealthy_cf"
	)
	if not stealthy_ran:
		verdict = "INVALID_stealthy_did_not_run"
	elif (sc["ok_rate"] or 0) > (cr["ok_rate"] or 0) + 0.08:
		verdict = "stealthy_more_reliable_than_our_chromium"
	elif (cr["ok_rate"] or 0) > (sc["ok_rate"] or 0) + 0.08:
		verdict = "our_chromium_more_reliable_than_stealthy"
	elif len(sc.get("unlocked_vs_http_ours") or []) > len(hs.get("unlocked_vs_http_ours") or []):
		verdict = "stealthy_unlocks_more_than_http_tls_alone"
	elif (sc["ok_rate"] or 0) >= (cr["ok_rate"] or 0) and (sc.get("mean_previews_ok") or 0) > (
		cr.get("mean_previews_ok") or 0
	):
		verdict = "stealthy_similar_or_better_content_yield"
	else:
		verdict = "tie_or_mixed_on_this_hard_set"

	out = {
		"verdict": verdict,
		"summaries": summaries,
		"rows": [asdict(r) for r in rows],
		"methodology": {
			"stealthy_cf": "AsyncStealthySession reused; solve_cloudflare=True; headless",
			"chromium_ours": "InspirationBrowserSession headless + force_kill per URL",
			"http_scrapling": "FetcherSession TLS only (not Stealthy)",
			"note": "Sync StealthySession cannot run inside asyncio — use AsyncStealthySession",
		},
	}
	log(f"\nVERDICT: {verdict}")
	report = Path("docs/research/scrapling_stealthy_results.json")
	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text(json.dumps(out, indent=2), encoding="utf-8")
	log(f"Wrote {report}")
	return 0


def main() -> int:
	return asyncio.run(main_async())


if __name__ == "__main__":
	raise SystemExit(main())
