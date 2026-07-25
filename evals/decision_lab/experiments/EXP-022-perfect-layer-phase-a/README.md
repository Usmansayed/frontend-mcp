# EXP-022 — Perfect Layer Phase A (slim card + fingerprint skip)

**Date:** 2026-07-18  
**Status:** done  
**Track:** Perfect Coordination Layer Phase A

## Hypothesis

Fingerprint skip after strategy compile must not stale host honesty (EVIDENCE THIN). Section completion must invalidate fingerprint.

## Lab lock

`scenarios/slim_coordinator_card.yaml` — thin snapshot twice; host still shows EVIDENCE THIN.

## Bench (report-only)

`python scripts/bench_coordinator_bridge.py --n 30` on this machine:

- p50 ≈ 0.35ms, p95 ≈ 0.41ms (target p95 < 50ms — **YES**)

See `bench.json`.

## Verdict

**Win** — baseline **23/23**; slim `coordinator_card.v1` + fingerprint skip.
