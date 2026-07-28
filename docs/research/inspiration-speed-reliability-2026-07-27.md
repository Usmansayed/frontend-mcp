# Inspiration speed & reliability — R&D notes

**Date:** 2026-07-27  
**Scope:** Inspiration Intelligence collect/discover (levels + multi-scout)

## Problem (measured)

Live profiling of `inspiration_level=wide` on dashboard/ecommerce intents **hung** for minutes with Chromium `BrowserSession` logs.

Root cause:

1. `wide` mapped to planner mode `broad`, which used `IMAGE_FIRST_PROVIDER_ORDER` including **dribbble / awwwards / godly**.
2. Intent prefer lists put **dribbble** near the front for dashboards (`prefer_providers: behance, dribbble, …`).
3. Concurrent wave **peels leading browser providers first** → headed Chromium before HTTP wins.
4. `prefer_browser=True` providers (awwwards/godly) always open Chromium even when `INSPIRATION_FAST=1`.
5. No hard wall-clock deadline on collect → one WAF hang stalls the whole MCP tool.

Secondary issues:

- Multi-scout ran **after** HTTP serially → wide wall ≈ http + scout instead of max(http, scout).
- Soft budgets existed in levels, but were not enforced as fail-closed deadlines.

## Changes shipped

| Fix | Why |
|-----|-----|
| `wide` / `broad` = HTTP + siteinspire only; **no WAF browsers** | Breadth comes from corpus multi-scout, not Chromium |
| Intent prefer lists drop dribbble/awwwards as defaults | Stop prefer-pinning WAF galleries |
| Prefer reorder always keeps HTTP before browser | Even on `max`, never peel dribbble first |
| `max` caps browser-heavy galleries to **1** | Research allowed, hang surface minimized |
| Level field `include_browser_galleries` + collect hard-strip | Defense in depth vs planner drift |
| `hard_deadline_s` (~budget × 1.25) checked between phases | Fail-closed MCP latency |
| Overlap multi-scout with HTTP (`overlap_scout`) | Wall ≈ max(http, scout) for standard/wide/max |
| Tighter provider timeouts (5–8s by level) | Propagated into concurrent wave |
| Shared HTTP opener | Amortize TLS setup under scout fan-out |

## Live smoke (post-fix, materialize off, cache off)

Expect:

- `light` / `standard` / `wide` on dashboard queries complete under hard deadline without BrowserSession.
- `wide` may still run multi-scout; `providers` must not include dribbble/awwwards/godly.

## Still open (next R&D)

- aiohttp / httpx connection pool instead of urllib threads
- Sticky provider health by intent class (boost winners for 15m)
- Preview HEAD validation before counting a ref as usable
- Cancel Chromium cleanly on `asyncio.TimeoutError` (session leak risk on `max`)
- Blob materialize latency under frequent MCP (parallel already; tune JPEG size)

## Agent contract (unchanged shape)

```text
collect({ query, inspiration_level: "standard" })
```

Read `perception://guide/inspiration`. Prefer **standard**; use **max** only when you knowingly want a time-boxed browser gallery.
