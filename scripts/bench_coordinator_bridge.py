#!/usr/bin/env python3
"""Time CoordinatorBridge.process on fixture envelopes. Report-only (no CI fail)."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.integration.bridge import CoordinatorBridge
from navigation.core.envelope import make_envelope


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=50, help="iterations after warmup")
    parser.add_argument("--json", type=Path, default=None, help="optional output path")
    args = parser.parse_args()

    bridge = CoordinatorBridge()
    bridge.process(
        "perception_session_start",
        {
            "base_url": "http://localhost:5173",
            "intent": "redesign Meridian analytics dashboard",
        },
        make_envelope(
            "perception_session_start",
            ok=True,
            session_id="bench_coord",
            url="http://localhost:5173",
        ),
    )

    samples_ms: list[float] = []
    for i in range(args.n + 5):
        env = make_envelope(
            "perception_navigate_and_observe",
            ok=True,
            session_id="bench_coord",
            data={
                "url": "http://localhost:5173/dashboard",
                "scan_id": f"bench_{i}",
                "agent_summary": {"blocking": []},
            },
        )
        t0 = time.perf_counter()
        bridge.process(
            "perception_navigate_and_observe",
            {"session_id": "bench_coord"},
            env,
        )
        elapsed = (time.perf_counter() - t0) * 1000.0
        if i >= 5:
            samples_ms.append(elapsed)

    samples_ms.sort()
    p50 = statistics.median(samples_ms)
    p95 = _percentile(samples_ms, 95)
    report = {
        "n": len(samples_ms),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(max(samples_ms), 3),
        "target_p95_ms": 50.0,
        "under_target": p95 < 50.0,
    }
    print(
        f"CoordinatorBridge observe hot path: n={report['n']} "
        f"p50={report['p50_ms']}ms p95={report['p95_ms']}ms "
        f"max={report['max_ms']}ms target_p95<50={'YES' if report['under_target'] else 'NO'}"
    )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
