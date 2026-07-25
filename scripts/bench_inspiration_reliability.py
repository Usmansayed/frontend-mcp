#!/usr/bin/env python3
"""Continuous reliability loop for inspiration: search → URLs → temp blobs.

Default path uses HTTP-friendly providers only (onepagelove, behance) so the
MCP happy path stays fast and anti-bot-safe.

Usage:
  python scripts/bench_inspiration_reliability.py
  python scripts/bench_inspiration_reliability.py --rounds 5 --query "saas landing page"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Bypass cooldown between continuous rounds; keep FAST for early-stop.
os.environ.setdefault("INSPIRATION_FORCE", "1")
os.environ.setdefault("INSPIRATION_FAST", "1")
os.environ.setdefault("INSPIRATION_HEADLESS", "true")
os.environ.setdefault("INSPIRATION_ALLOW_BROWSER_SCREENSHOT", "0")

from navigation.inspiration_intelligence.collect import collect_inspiration_hits
from navigation.inspiration_intelligence.models import InspirationDiscoveryRequest
from navigation.inspiration_intelligence.service import InspirationIntelligenceService
from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

# Anti-bot-friendly defaults for the MCP happy path.
FAST_PROVIDERS = ["onepagelove", "lapa", "behance", "httpster", "siteinspire"]

DEFAULT_QUERIES = [
	"saas landing page",
	"clean white product landing",
	"professional dashboard ui",
]


def _round_ok(manifest: dict[str, Any], *, min_refs: int, require_blobs: bool) -> tuple[bool, list[str]]:
	fails: list[str] = []
	hits = int(manifest.get("total_hits") or 0)
	with_urls = int(manifest.get("total_with_urls") or 0)
	bs = manifest.get("blob_summary") or {}
	materialized = int(bs.get("materialized") or 0)
	failed_blobs = int(bs.get("failed") or 0)

	if with_urls < min_refs:
		fails.append(f"urls={with_urls}<{min_refs}")
	if require_blobs and materialized < min(min_refs, with_urls):
		fails.append(f"blobs={materialized}<needed (failed={failed_blobs})")
	if hits <= 0:
		fails.append("zero_hits")
	return (not fails), fails


async def _run_collect(
	query: str,
	*,
	providers: list[str],
	out_dir: Path,
	min_refs: int,
	target_refs: int,
) -> dict[str, Any]:
	t0 = time.perf_counter()
	manifest = await collect_inspiration_hits(
		query,
		out_dir,
		per_provider=4,
		provider_ids=providers,
		download_images=False,
		materialize_blobs=True,
		write_per_hit_files=False,
		target_refs=target_refs,
		min_refs=min_refs,
		allow_browser_screenshot=False,
		max_queries=3,
	)
	elapsed_ms = (time.perf_counter() - t0) * 1000.0
	ok, fails = _round_ok(manifest, min_refs=min_refs, require_blobs=True)
	providers_used = sorted(
		{
			str((h.get("provider_id") if isinstance(h, dict) else getattr(h, "provider_id", "")) or "")
			for h in (manifest.get("hits") or [])
		}
		- {""}
	)
	# Prefer provider_summary keys when hits shape differs
	if not providers_used and isinstance(manifest.get("provider_summary"), dict):
		providers_used = sorted(str(k) for k in manifest["provider_summary"].keys())

	return {
		"ok": ok,
		"failures": fails,
		"elapsed_ms": round(elapsed_ms, 1),
		"query": query,
		"total_hits": manifest.get("total_hits"),
		"total_with_urls": manifest.get("total_with_urls"),
		"blob_summary": manifest.get("blob_summary"),
		"blob_session_id": manifest.get("blob_session_id"),
		"stopped_early": manifest.get("stopped_early"),
		"stop_reason": manifest.get("stop_reason"),
		"queries_used": manifest.get("queries_used"),
		"providers_used": providers_used,
		"provider_summary": manifest.get("provider_summary"),
	}


async def _run_discover(query: str, *, providers: list[str]) -> dict[str, Any]:
	svc = InspirationIntelligenceService()
	# Prefer first HTTP-friendly provider; early-stop usually avoids browser galleries.
	preference = providers[0] if providers else "onepagelove"
	t0 = time.perf_counter()
	result = await svc.discover(
		InspirationDiscoveryRequest(
			query=query,
			max_candidates=8,
			provider_preference=preference,
		)
	)
	elapsed_ms = (time.perf_counter() - t0) * 1000.0
	n = len(result.candidates)
	# Count how many came from our fast provider set
	from_fast = sum(1 for c in result.candidates if c.candidate.provider_id in set(providers))
	return {
		"ok": n > 0 and from_fast > 0,
		"elapsed_ms": round(elapsed_ms, 1),
		"candidate_count": n,
		"from_fast_providers": from_fast,
		"degraded": list(result.degraded)[:12],
		"provider_ids_plan": list(result.search_plan.provider_ids),
	}


async def main_async(args: argparse.Namespace) -> int:
	providers = list(args.providers) if args.providers else list(FAST_PROVIDERS)
	queries = list(args.queries) if args.queries else list(DEFAULT_QUERIES)
	stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
	out_root = ROOT / "artifacts" / "inspiration_reliability" / stamp
	out_root.mkdir(parents=True, exist_ok=True)

	rounds: list[dict[str, Any]] = []
	print(f"Providers: {providers}")
	print(f"Rounds: {args.rounds} | min_refs={args.min_refs} | target={args.target_refs}")
	print(f"Output: {out_root}")
	print("=" * 60)

	for i in range(args.rounds):
		query = queries[i % len(queries)] if not args.query else args.query
		round_dir = out_root / f"round_{i + 1:02d}"
		round_dir.mkdir(parents=True, exist_ok=True)

		discover = await _run_discover(query, providers=providers)
		collect = await _run_collect(
			query,
			providers=providers,
			out_dir=round_dir,
			min_refs=args.min_refs,
			target_refs=args.target_refs,
		)

		# Cleanup blobs so continuous runs don't fill disk
		sid = collect.get("blob_session_id")
		if sid:
			try:
				InspirationBlobStore().end_session(str(sid))
			except Exception as exc:  # noqa: BLE001
				collect.setdefault("failures", []).append(f"blob_cleanup:{exc}")

		row = {
			"round": i + 1,
			"query": query,
			"discover": discover,
			"collect": collect,
			"ok": bool(discover.get("ok")) and bool(collect.get("ok")),
		}
		rounds.append(row)
		status = "PASS" if row["ok"] else "FAIL"
		print(
			f"[{status}] round {i + 1}/{args.rounds} q={query!r} "
			f"discover={discover.get('elapsed_ms')}ms/{discover.get('candidate_count')}c "
			f"collect={collect.get('elapsed_ms')}ms "
			f"urls={collect.get('total_with_urls')} "
			f"blobs={(collect.get('blob_summary') or {}).get('materialized')} "
			f"providers={collect.get('providers_used')} "
			f"fails={collect.get('failures')}"
		)

		# Small pause so CDNs aren't hammered even with FORCE
		await asyncio.sleep(args.pause_s)

	lat_collect = [float(r["collect"]["elapsed_ms"]) for r in rounds]
	lat_discover = [float(r["discover"]["elapsed_ms"]) for r in rounds]
	pass_n = sum(1 for r in rounds if r["ok"])
	summary = {
		"stamp": stamp,
		"providers": providers,
		"rounds": args.rounds,
		"pass_count": pass_n,
		"fail_count": args.rounds - pass_n,
		"pass_rate": round(pass_n / max(args.rounds, 1), 3),
		"discover_ms": {
			"p50": round(statistics.median(lat_discover), 1),
			"max": round(max(lat_discover), 1),
		},
		"collect_ms": {
			"p50": round(statistics.median(lat_collect), 1),
			"max": round(max(lat_collect), 1),
			"target_p95_under_ms": args.budget_ms,
		},
		"budget_ok": statistics.median(lat_collect) <= args.budget_ms,
		"rounds_detail": rounds,
	}
	(out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
	print("=" * 60)
	print(
		f"PASS {pass_n}/{args.rounds} ({summary['pass_rate'] * 100:.0f}%) | "
		f"discover p50={summary['discover_ms']['p50']}ms | "
		f"collect p50={summary['collect_ms']['p50']}ms max={summary['collect_ms']['max']}ms | "
		f"budget_ok={summary['budget_ok']} (<={args.budget_ms}ms p50)"
	)
	print(f"Wrote {out_root / 'summary.json'}")

	# Success criteria: ≥80% pass and collect p50 under budget
	if pass_n / max(args.rounds, 1) < 0.8:
		return 2
	if not summary["budget_ok"]:
		return 3
	return 0


def main() -> int:
	parser = argparse.ArgumentParser(description="Continuous inspiration reliability bench")
	parser.add_argument("--rounds", type=int, default=5)
	parser.add_argument("--query", default=None, help="Fixed query for all rounds")
	parser.add_argument("--queries", nargs="*", default=None)
	parser.add_argument("--providers", nargs="*", default=None)
	parser.add_argument("--min-refs", type=int, default=3)
	parser.add_argument("--target-refs", type=int, default=5)
	parser.add_argument("--pause-s", type=float, default=2.0)
	parser.add_argument("--budget-ms", type=float, default=15000.0, help="Collect p50 budget")
	args = parser.parse_args()
	return asyncio.run(main_async(args))


if __name__ == "__main__":
	raise SystemExit(main())
