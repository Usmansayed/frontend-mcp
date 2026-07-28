#!/usr/bin/env python3
"""Inspiration fast-path perf harness — records collect_ms / provider_ms.

Usage (from repo root, with network):
  INSPIRATION_FAST=1 python -m evals.inspiration_perf_harness "saas landing page"

Writes JSON summary to evals/results/inspiration_perf_*.json when possible.
Mock/offline unit budgets live in tests/test_inspiration_live_and_perf.py.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


async def run(query: str, *, mode: str = "fast") -> dict:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	t0 = time.perf_counter()
	manifest = await collect_inspiration_hits(
		query,
		mode=mode,
		include_live_sites=False,
		materialize_blobs=True,
		target_refs=5,
		min_refs=3,
	)
	wall_s = time.perf_counter() - t0
	summary = {
		"query": query,
		"mode": mode,
		"wall_s": round(wall_s, 3),
		"collect_ms": manifest.get("collect_ms"),
		"total_hits": manifest.get("total_hits"),
		"image_ref_count": manifest.get("image_ref_count"),
		"stopped_early": manifest.get("stopped_early"),
		"stop_reason": manifest.get("stop_reason"),
		"provider_ms": manifest.get("provider_ms"),
		"budget_ok_15s": wall_s < 15.0,
		"recorded_at": datetime.now(timezone.utc).isoformat(),
	}
	return summary


def main() -> int:
	query = " ".join(sys.argv[1:]).strip() or "saas landing page"
	summary = asyncio.run(run(query))
	print(json.dumps(summary, indent=2))
	out_dir = ROOT / "evals" / "results"
	try:
		out_dir.mkdir(parents=True, exist_ok=True)
		stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
		path = out_dir / f"inspiration_perf_{stamp}.json"
		path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
		print(f"wrote {path}", file=sys.stderr)
	except OSError as exc:
		print(f"could not write results: {exc}", file=sys.stderr)
	return 0 if summary.get("budget_ok_15s") else 1


if __name__ == "__main__":
	raise SystemExit(main())
