#!/usr/bin/env python3
"""Inspiration matrix bench — per-website reliability + speed.

For each gallery provider: run 5 search queries × N trials through the full
collect path (search → preview URLs → download/materialize blobs).

Usage:
  python scripts/bench_inspiration_matrix.py
  python scripts/bench_inspiration_matrix.py --trials 5 --providers onepagelove behance siteinspire
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("INSPIRATION_FORCE", "1")
os.environ.setdefault("INSPIRATION_FAST", "0")  # pin providers explicitly
os.environ.setdefault("INSPIRATION_HEADLESS", "true")
os.environ.setdefault("INSPIRATION_ALLOW_BROWSER_SCREENSHOT", "0")

from navigation.inspiration_intelligence.collect import collect_inspiration_hits
from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

ALL_PROVIDERS = [
    "onepagelove",
    "lapa",
    "behance",
    "httpster",
    "siteinspire",
    "dribbble",
    "awwwards",
    "godly",
]

DEFAULT_QUERIES = [
    "saas landing page",
    "analytics dashboard ui",
    "clean product marketing page",
    "admin panel interface",
    "fintech mobile app ui",
]


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


async def _one_run(
    *,
    provider: str,
    query: str,
    out_dir: Path,
    min_refs: int,
    target_refs: int,
    download_images: bool,
    allow_browser: bool,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    err: str | None = None
    manifest: dict[str, Any] = {}
    try:
        manifest = await collect_inspiration_hits(
            query,
            out_dir,
            per_provider=4,
            provider_ids=[provider],
            download_images=download_images,
            materialize_blobs=True,
            write_per_hit_files=False,
            target_refs=target_refs,
            min_refs=min_refs,
            allow_browser_screenshot=allow_browser,
            max_queries=2,
        )
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    hits = list(manifest.get("hits") or [])
    with_urls = int(manifest.get("total_with_urls") or 0)
    bs = manifest.get("blob_summary") or {}
    materialized = int(bs.get("materialized") or 0)
    failed_blobs = int(bs.get("failed") or 0)
    degraded = []
    for h in hits:
        if isinstance(h, dict):
            degraded.extend(list(h.get("degraded") or []))
    # Unique degraded tags
    deg_u = sorted({str(d) for d in degraded})[:12]

    ok = (not err) and with_urls >= min_refs and materialized >= min(min_refs, max(with_urls, 1))
    sid = manifest.get("blob_session_id")
    if sid:
        try:
            InspirationBlobStore().end_session(str(sid))
        except Exception:  # noqa: BLE001
            pass

    return {
        "ok": ok,
        "error": err,
        "elapsed_ms": round(elapsed_ms, 1),
        "provider": provider,
        "query": query,
        "total_hits": manifest.get("total_hits") or 0,
        "total_with_urls": with_urls,
        "blobs_materialized": materialized,
        "blobs_failed": failed_blobs,
        "stopped_early": bool(manifest.get("stopped_early")),
        "stop_reason": manifest.get("stop_reason"),
        "queries_used": manifest.get("queries_used"),
        "degraded": deg_u,
        "provider_summary": manifest.get("provider_summary"),
    }


async def main_async(args: argparse.Namespace) -> int:
    providers = list(args.providers) if args.providers else list(ALL_PROVIDERS)
    queries = list(args.queries) if args.queries else list(DEFAULT_QUERIES)
    trials = max(1, int(args.trials))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_root = ROOT / "artifacts" / "inspiration_matrix" / stamp
    out_root.mkdir(parents=True, exist_ok=True)

    total = len(providers) * len(queries) * trials
    print(f"Inspiration matrix bench")
    print(f"  providers ({len(providers)}): {providers}")
    print(f"  queries   ({len(queries)}): {queries}")
    print(f"  trials/query: {trials}  ->  total runs: {total}")
    print(f"  download_images={args.download_images}  allow_browser={args.allow_browser}")
    print(f"  output: {out_root}")
    print("=" * 72)

    rows: list[dict[str, Any]] = []
    n = 0
    for provider in providers:
        for query in queries:
            for trial in range(1, trials + 1):
                n += 1
                run_dir = out_root / provider / f"q_{slug(query)}" / f"trial_{trial:02d}"
                run_dir.mkdir(parents=True, exist_ok=True)
                print(f"\n[{n}/{total}] {provider} | trial {trial}/{trials} | {query!r}")
                row = await _one_run(
                    provider=provider,
                    query=query,
                    out_dir=run_dir,
                    min_refs=args.min_refs,
                    target_refs=args.target_refs,
                    download_images=args.download_images,
                    allow_browser=args.allow_browser,
                )
                row["trial"] = trial
                rows.append(row)
                status = "PASS" if row["ok"] else "FAIL"
                print(
                    f"  → {status}  {row['elapsed_ms']:.0f}ms  "
                    f"hits={row['total_hits']} urls={row['total_with_urls']} "
                    f"blobs={row['blobs_materialized']} fail_blobs={row['blobs_failed']} "
                    f"err={row['error']!r} deg={row['degraded'][:4]}"
                )
                # Persist progress so a long run is inspectable mid-flight
                (out_root / "progress.json").write_text(
                    json.dumps({"completed": n, "total": total, "rows": rows}, indent=2),
                    encoding="utf-8",
                )
                await asyncio.sleep(args.pause_s)

    # Per-provider rollup
    by_prov: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_prov[str(r["provider"])].append(r)

    provider_stats: list[dict[str, Any]] = []
    for provider in providers:
        rs = by_prov.get(provider) or []
        lats = [float(r["elapsed_ms"]) for r in rs]
        ok_n = sum(1 for r in rs if r["ok"])
        urls = [int(r["total_with_urls"]) for r in rs]
        blobs = [int(r["blobs_materialized"]) for r in rs]
        errs = [r["error"] for r in rs if r.get("error")]
        deg_counts: dict[str, int] = defaultdict(int)
        for r in rs:
            for d in r.get("degraded") or []:
                deg_counts[str(d)] += 1
        provider_stats.append({
            "provider": provider,
            "runs": len(rs),
            "pass": ok_n,
            "fail": len(rs) - ok_n,
            "pass_rate": round(ok_n / max(len(rs), 1), 3),
            "elapsed_ms": {
                "p50": round(_pct(lats, 0.5), 1),
                "p95": round(_pct(lats, 0.95), 1),
                "max": round(max(lats) if lats else 0.0, 1),
                "mean": round(statistics.mean(lats), 1) if lats else 0.0,
            },
            "urls": {
                "mean": round(statistics.mean(urls), 2) if urls else 0.0,
                "min": min(urls) if urls else 0,
                "max": max(urls) if urls else 0,
            },
            "blobs_materialized": {
                "mean": round(statistics.mean(blobs), 2) if blobs else 0.0,
                "min": min(blobs) if blobs else 0,
                "max": max(blobs) if blobs else 0,
            },
            "top_errors": errs[:5],
            "degraded_top": sorted(deg_counts.items(), key=lambda x: -x[1])[:8],
        })

    summary = {
        "stamp": stamp,
        "providers": providers,
        "queries": queries,
        "trials": trials,
        "total_runs": len(rows),
        "pass_count": sum(1 for r in rows if r["ok"]),
        "fail_count": sum(1 for r in rows if not r["ok"]),
        "download_images": args.download_images,
        "allow_browser": args.allow_browser,
        "provider_stats": provider_stats,
        "rows": rows,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Human table
    print("\n" + "=" * 72)
    print(f"{'provider':<14} {'pass%':>6} {'p50ms':>8} {'p95ms':>8} {'maxms':>8} {'urlsμ':>6} {'blobμ':>6}")
    print("-" * 72)
    for s in provider_stats:
        print(
            f"{s['provider']:<14} {s['pass_rate']*100:5.0f}% "
            f"{s['elapsed_ms']['p50']:8.0f} {s['elapsed_ms']['p95']:8.0f} "
            f"{s['elapsed_ms']['max']:8.0f} {s['urls']['mean']:6.1f} {s['blobs_materialized']['mean']:6.1f}"
        )
    print("=" * 72)
    print(f"Wrote {out_root / 'summary.json'}")
    print(f"Overall pass: {summary['pass_count']}/{summary['total_runs']}")
    return 0 if summary["pass_count"] == summary["total_runs"] else 1


def slug(q: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in q.lower())[:48].strip("_")


def main() -> int:
    p = argparse.ArgumentParser(description="Per-website inspiration reliability matrix")
    p.add_argument("--providers", nargs="*", default=None)
    p.add_argument("--queries", nargs="*", default=None)
    p.add_argument("--trials", type=int, default=5, help="Repeats per (provider, query)")
    p.add_argument("--min-refs", type=int, default=3)
    p.add_argument("--target-refs", type=int, default=5)
    p.add_argument("--pause-s", type=float, default=1.0)
    p.add_argument("--download-images", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--allow-browser",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Allow browser screenshot fallback (slow; off by default for fair HTTP timing)",
    )
    args = p.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
