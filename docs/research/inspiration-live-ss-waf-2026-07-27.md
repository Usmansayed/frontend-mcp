# Live Chromium / WAF harden — research + ship

**Date:** 2026-07-27  
**Problem:** Live screenshots were gated off in evals because WAF/timeouts burned budget and leaked Chromium.

## Research findings

| Failure | Cause |
|---------|--------|
| Stub PNG burn | Navigate captured screenshot *before* block detect |
| Budget blow | wide/max could schedule 2–4×~10s SS past hard deadline |
| WAF lottery | Web SS used raw SERP hosts, not OG-validated pages |
| Headless vs headed | Live forced headless; galleries use headed |
| Overlap | No global lock across web SS + famous + scout |
| Host retry thrash | Same blocked host retried every collect |

## Shipped improvisations

| Fix | Behavior |
|-----|----------|
| **Block-before-screenshot** | Navigate `screenshot=False` → detect block → only then CDP capture |
| **Host cooldown** (~20m) | Skip Chromium for hosts that already blocked |
| **Global capture lock** | Singleton browser — no interleaved captures |
| **Deadline-aware SS** | Abort wave if &lt;6s remaining on hard deadline |
| **OG-prefer web SS** | Screenshot pages that already yielded OG, not raw SERP |
| **Level gating** | `wide.max_web_screenshots=0`; `max` capped at **2** |
| **Headed retry** | After bot_challenge, one headed retry (env `INSPIRATION_HEADED_RETRY=1`) |
| **Park-safe force_kill** | Restore parked URL before Chromium reset |

Fast HTTP/pattern path unchanged (light/standard still SS-off by default).

## Still deferred

- Third-party screenshot proxies (Microlink/Screenshotone) for open web
- Durable multi-replica cooldown store
- Coordination “use inspiration for most tasks”

## Verification

- Unit: `tests/test_live_ss_harden.py` — pass
- Bounded stress: `scripts/eval_live_ss_stress.py` — **4/4** (HTTP packs when live SS skipped/gated)
- Hardcore HTTP battery — **13/13**

## Honest limit

Full Chromium capture on Windows can still **block the event loop** past `asyncio.wait_for` (Playwright/CDP). Guards prevent budget blow and stub PNGs; they do not make every live site screenshot reliable. Treat live SS as **best-effort bonus** on `max`; HTTP/pattern remains the production path.

Optional next: subprocess-isolated capture worker, or third-party screenshot API for Channel C.
