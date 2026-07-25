#!/usr/bin/env python3
"""Print scoreboard from inspiration matrix progress/summary JSON."""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    if not path.is_file():
        # latest progress
        root = Path(__file__).resolve().parents[1] / "artifacts" / "inspiration_matrix"
        cands = sorted(root.glob("*/progress.json")) + sorted(root.glob("*/summary.json"))
        if not cands:
            raise SystemExit("no progress/summary found")
        path = cands[-1]
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows") or data.get("rounds_detail") or []
    print(f"source: {path}")
    print(f"rows: {len(rows)}  completed_field: {data.get('completed')}")
    by: dict[str, list] = defaultdict(list)
    for r in rows:
        by[str(r["provider"])].append(r)
    order = [
        "onepagelove",
        "lapa",
        "behance",
        "httpster",
        "siteinspire",
        "dribbble",
        "awwwards",
        "godly",
    ]
    print(
        f"{'provider':<14} {'n':>3} {'blobOK':>7} {'urlOK':>6} "
        f"{'p50ms':>8} {'p95ms':>8} {'maxms':>8} {'url_mu':>7} {'blob_mu':>7}"
    )
    for prov in order:
        rs = by.get(prov) or []
        if not rs:
            continue
        blob_ok = sum(1 for r in rs if int(r.get("blobs_materialized") or 0) >= 3)
        url_ok = sum(1 for r in rs if int(r.get("total_with_urls") or 0) >= 3)
        ms = [float(r["elapsed_ms"]) for r in rs]
        urls = [int(r.get("total_with_urls") or 0) for r in rs]
        blobs = [int(r.get("blobs_materialized") or 0) for r in rs]
        print(
            f"{prov:<14} {len(rs):3} {blob_ok/len(rs)*100:6.0f}% {url_ok/len(rs)*100:5.0f}% "
            f"{pct(ms, 0.5):8.0f} {pct(ms, 0.95):8.0f} {max(ms):8.0f} "
            f"{statistics.mean(urls):7.1f} {statistics.mean(blobs):7.1f}"
        )


if __name__ == "__main__":
    main()
