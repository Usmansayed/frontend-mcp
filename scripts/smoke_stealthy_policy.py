"""Smoke: default fast path + auto TLS Scrapling on LAPA."""
from __future__ import annotations

import asyncio
import os
import time

os.environ.pop("INSPIRATION_HTTP_BACKEND", None)


def main() -> int:
	from navigation.inspiration_intelligence.browser.fetch import http_get
	from navigation.inspiration_intelligence.browser.stealthy_fallback import (
		reset_stealthy_budget_for_tests,
		should_try_stealthy,
	)
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	reset_stealthy_budget_for_tests()
	assert not should_try_stealthy(
		"https://www.saasframe.io/x", blocked=True, fast_mode=True
	)
	print("policy ok: saasframe skipped in fast")
	assert should_try_stealthy(
		"https://dribbble.com/search/login", blocked=True, fast_mode=True
	)
	print("policy ok: dribbble eligible for stealthy recovery even in fast")

	t0 = time.perf_counter()
	body, st, err = http_get("https://www.lapa.ninja/?s=saas", timeout=10, max_bytes=80_000)
	ms = (time.perf_counter() - t0) * 1000
	print(f"lapa http_get status={st} bytes={len(body or '')} ms={ms:.0f} err={err}")
	assert st == 200 and body, "LAPA should unlock via auto scrapling TLS"
	print("lapa auto TLS scrapling OK")

	t0 = time.perf_counter()
	manifest = asyncio.run(
		collect_inspiration_hits(
			"login form saas",
			inspiration_level="light",
			materialize_blobs=False,
			write_per_hit_files=False,
			include_live_sites=False,
			include_web_search=True,
			max_web_screenshots=0,
			use_result_cache=False,
			use_multi_scout=False,
		)
	)
	hits = int(manifest.get("total_hits") or len(manifest.get("hits") or []))
	print(f"collect light hits={hits} wall_s={time.perf_counter() - t0:.2f}")
	assert hits >= 3
	print("SMOKE PASS")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
