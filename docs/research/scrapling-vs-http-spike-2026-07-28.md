# Research: Scrapling — proper usage vs our inspiration HTTP path

**Date:** 2026-07-28 (revised after fair retest)  
**Library:** [d4vinci/Scrapling](https://github.com/d4vinci/Scrapling) v0.4.12 (BSD-3-Clause)  
**Docs:** [HTTP / FetcherSession](https://scrapling.readthedocs.io/en/latest/fetching/static.html)  
**Spike script:** `scripts/eval_scrapling_vs_http.py`  
**Raw results:** `docs/research/scrapling_spike_results.json`  
**Integration:** `browser/scrapling_pool.py` + `INSPIRATION_HTTP_BACKEND` in `browser/fetch.py`

---

## What we got wrong the first time

Scrapling’s own docs:

> The `Fetcher` class uses `FetcherSession` to create a **temporary session with each request**.  
> Session benefits: **a lot faster** (they claim ~10×), cookie persistence, connection pooling.

Our first spike compared **ours (warm httpx pool)** vs **cold `Fetcher.get`**. That unfairly made Scrapling look ~5× slower. Friend was right that Scrapling is powerful — we weren’t using the recommended API.

### Proper Scrapling surfaces (for our stack)

| API | Role for Inspiration |
|-----|----------------------|
| **`FetcherSession`** (sync, process-wide) | Fair peer to httpx keep-alive — **this is what we should use** |
| **`async with FetcherSession` + gather** | Concurrent fan-out (Scrapling’s recommended async pattern) |
| **`Fetcher.get` / `AsyncFetcher.get`** | One-offs / demos only — **not** for scout fan-out |
| **`StealthyFetcher` / `DynamicFetcher`** | Cloudflare JS challenges — we already have Chromium SS; skip for CDN galleries |
| **Adaptive CSS / spiders** | Hostile single-site scrapers — different product than multi-gallery inspire |

Also: Scrapling defaults **`retries=3`, `retry_delay=1`**. Under scout fan-out that inflates latency on soft failures. Our pool uses **`retries=1`, `retry_delay=0`** to match fail-fast inspiration policy.

---

## Fair methodology (this run)

Engines:

1. **ours** — httpx pool + urllib (`http_get` default)  
2. **scrapling_cold** — `Fetcher.get` (old / unfair)  
3. **scrapling_session** — process-wide `FetcherSession` (`scrapling_pool.py`)  
4. **hybrid** — ours first; Scrapling session on 403/block (`scrapling_fallback`)  
5. Bursts — ThreadPool n=8 (matches scout) + async `FetcherSession` gather  
6. **Integrated collect A/B** — same `collect_inspiration_hits` path, three backends, 3 queries

---

## Results (fair retest)

### Per-URL battery (best of 2 rounds)

| Engine | OK | Rate | p50 ms | p95 ms | Failed |
|--------|----|------|--------|--------|--------|
| **ours** | 10/12 | 0.833 | **42.6** | 767 | lapa, landbook |
| scrapling_cold | 10/12 | 0.833 | 339.5 | 919 | behance, landbook |
| **scrapling_session** | 10/12 | 0.833 | **119.3** | 750 | behance, landbook |
| **hybrid** | **11/12** | **0.917** | 110.4 | 714 | landbook only |

Session vs cold: **p50 119 vs 340 ms** (~2.8×). Cold penalty was real.

### Concurrent burst (n=8, friendly galleries)

| Engine | ok | wall_ms |
|--------|----|---------|
| ours | 8/8 | 518 |
| scrapling_cold | 8/8 | 536 |
| scrapling_session | 8/8 | 532 |
| hybrid | 8/8 | 177 (warm) |
| scrapling_async_session | 8/8 | 554 |

With a fair session, Scrapling **matches** our burst wall (~530 ms). It does **not** beat a warm httpx pool on friendly CDNs.

### Head-to-heads that matter

| Host | ours | scrapling_session | hybrid |
|------|------|-------------------|--------|
| **LAPA** | 403 | **200** + previews | **200** (Scrapling unlock) |
| **Behance** | **200** | 403 | **200** (keep ours) |
| Land-book | 403 | 404 | still fail |
| saasframe / navbar / footer | both 200 | both 200 | ours warmer |

### Integrated collect (`light`, 3 queries)

| Backend | login | checkout | pricing | All ≥3 hits? |
|---------|-------|----------|---------|--------------|
| ours | 4 / 1.2s | 5 / 1.1s | 4 / 0.5s | yes |
| scrapling | 4 / 0.7s | 4 / 0.5s | 4 / 0.5s | yes |
| hybrid | 4 / 0.2s | 4 / 0.2s | 4 / 0.3s | yes |

System-level: **no quality regression**; hybrid/scrapling not slower in this sample. (Collect wall is specialist+HTTP mix — don’t over-read absolute ms.)

**Verdict code:** `hybrid_best_reliability`

---

## Revised recommendation

1. **Default stays httpx/urllib** — still fastest warm path for friendly galleries.  
2. **Do not use cold `Fetcher.get` in production.**  
3. **Best integration = hybrid fallback** (`INSPIRATION_HTTP_BACKEND=scrapling_fallback`): keep Behance, unlock LAPA-class TLS blocks.  
4. Optional full replace (`=scrapling`) for experiments only — loses Behance on this suite.  
5. Keep Scrapling **optional** (not a hard MCP install dep).  
6. Skip Stealthy/Dynamic for inspiration collect — wrong cost curve vs CDN + specialists.

### Env knobs

```powershell
$env:PYTHONPATH="src"
# Fair session-only backend
$env:INSPIRATION_HTTP_BACKEND="scrapling"
# Recommended: ours + Scrapling on 403/block
$env:INSPIRATION_HTTP_BACKEND="scrapling_fallback"
python scripts/eval_scrapling_vs_http.py
```

Unset to restore default.

---

## What Scrapling is actually “powerful” for (beyond this path)

- TLS / browser impersonation that unblocks some WAFs (LAPA)  
- Session reuse + async gather for large crawls  
- Stealthy/Dynamic for Turnstile-class sites  
- Adaptive selectors + spiders for long-lived single-site scrapers  

Inspiration Intelligence’s bottleneck was never “need Scrapy.” Specialists, relevance, soft-floor already shipped. Scrapling’s **fair** win here is **narrow reliability (hybrid)**, not a wholesale speed upgrade.

---

## Code shipped this pass

- `src/navigation/inspiration_intelligence/browser/scrapling_pool.py` — process-wide `FetcherSession`  
- `browser/fetch.py` — `scrapling` + `scrapling_fallback` backends using the session pool  
- `scripts/eval_scrapling_vs_http.py` — cold vs session vs hybrid + burst + collect A/B  
