# Research: Scrapling StealthyFetcher vs our Chromium (hard hosts)

**Date:** 2026-07-28  
**Script:** `scripts/eval_scrapling_stealthy_vs_chromium.py`  
**Raw:** `docs/research/scrapling_stealthy_results.json`  
**Related:** HTTP-only spike in `scrapling-vs-http-spike-2026-07-28.md` (different question)

---

## Why this test exists

Friends saying Scrapling is “very powerful” almost always mean **`StealthyFetcher` / anti-bot browser**, not plain HTTP `Fetcher`.  
Our earlier HTTP bake-off was fair for CDN galleries — but it did **not** test Scrapling’s famous weapon.

This run compares hard inspiration hosts:

| Engine | What it is |
|--------|------------|
| `http_ours` | httpx pool |
| `http_scrapling` | `FetcherSession` (TLS impersonate only) |
| `chromium_ours` | `InspirationBrowserSession.fetch_html` (Perception Chromium, headless) |
| `stealthy_cf` | `AsyncStealthySession` + `solve_cloudflare=True` (session reused) |

Targets: Behance, Land-book, LAPA, Dribbble.

---

## Results

| Engine | OK | Rate | p50 (ok) | Unlocked vs `http_ours` fails |
|--------|----|------|----------|-------------------------------|
| http_ours | 1/4 | 0.25 | ~1s | — |
| http_scrapling | 2/4 | 0.50 | ~0.9s | landbook, **lapa** |
| chromium_ours | 2/4 | 0.50 | ~9.6s | **dribbble** |
| **stealthy_cf** | **4/4** | **1.00** | ~24s | dribbble, landbook, lapa |

### Per host

| Host | http_ours | http_scrapling | chromium_ours | stealthy_cf |
|------|-----------|----------------|---------------|-------------|
| Behance | 200 (weak prev) | 403 | 200 | **200** (~128s first) |
| Land-book | 403 | **200** | bot_challenge | **200** + 3 previews |
| LAPA | 403 | **200** + 8 prev | bot_challenge | **200** |
| Dribbble | 202 challenge | 202 | **200** + 8 prev | **200** + 8 prev |

**Verdict:** `stealthy_more_reliable_than_our_chromium`

Your friends were right about **this** layer.

---

## What that means (honest)

### Scrapling Stealthy is better at
- Getting past **bot challenges** our Perception Chromium still trips on (Land-book, LAPA in this run)
- **Dribbble** without a session cookie (both Chromium and Stealthy got 200 + 8 previews; HTTP both 202)
- Being a **dedicated anti-bot fetch stack** (fingerprint / CF tooling) out of the box

### Cost
- **Much slower**: Stealthy p50 ~24s vs Chromium ~10s vs HTTP &lt;1s  
- Behance first Stealthy fetch ~128s (CF solver waited even when no challenge found)  
- Heavier dependency (Camoufox / stealth browser stack)

### Our stack is still better at
- **Friendly CDN galleries** (saasframe, daisy, navbar) — HTTP path, sub-second  
- **Product integration** (park/restore Perception browser, region crop, MCP session)  
- **Default collect latency** — inspiration must stay fast; Stealthy cannot be the default for every hit

### Cheap middle ground (already proven)
`http_scrapling` / hybrid unlocks **LAPA + Land-book home** without a browser — often enough.

---

## Integration recommendation (revised)

1. Keep default collect = httpx + specialists (fast path).  
2. **Auto cheap TLS Scrapling** on WAF allowlist after 403/202 (`http_get` — LAPA-class).  
3. **Stealthy fallback** after our Chromium fails on allowlisted hosts (Dribbble, Land-book, LAPA, Behance, Awwwards):
   - `INSPIRATION_STEALTHY_FALLBACK=1` (default on)
   - skipped in fast mode unless `INSPIRATION_STEALTHY_IN_FAST=1`
   - budget: `INSPIRATION_STEALTHY_BUDGET=2` per process
   - timeout: `INSPIRATION_STEALTHY_TIMEOUT_MS=28000`
4. Do **not** replace Perception Chromium wholesale — Stealthy is last resort.  
5. Module: `browser/stealthy_fallback.py`; wired in Dribbble + `resilient_fetch`.

See also: product wiring note in this file’s parent conversation (2026-07-28).

---

## Method notes / pitfalls

- Sync `StealthySession` **cannot** run inside our asyncio loop → use **`AsyncStealthySession`**.  
- Response body is `html_content` / `body` (bytes), not `.html`.  
- `solve_cloudflare=True` logs “No Cloudflare challenge found” often — still returns pages; costs wait time.  
- First hung run used cold per-URL browser churn; lean script reuses one Stealthy session.

---

## Bottom line for the skeptical question

| Claim | True? |
|-------|-------|
| “Scrapling is a very powerful scraping tool” | **Yes** — especially Stealthy on hard hosts (4/4 here). |
| “Our system is better than Scrapling overall” | **No** as a general claim. |
| “Our default inspiration HTTP is better for friendly galleries” | **Yes** (speed). |
| “We should use Stealthy as the always-on fetch path” | **No** — too slow for collect UX; use as **hard-host fallback**. |
