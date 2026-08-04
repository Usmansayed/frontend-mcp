# Inspiration Layer Enlargement — Research Findings

**Date:** 2026-07-26  
**Status:** research complete (spike + taxonomy + channel design)  
**Parent plan:** [2026-07-26-inspiration-first-design-loop.md](../plans/2026-07-26-inspiration-first-design-loop.md)  
**Architecture:** [inspiration-concurrent-architecture.md](../plans/inspiration-concurrent-architecture.md)

## Thesis (confirmed)

Inspiration Intelligence is the **creative acquisition engine**:

1. **Decide where to look** — planner / source taxonomy (`fast` | `broad` | `deep`)
2. **Acquire visual refs fast** — gallery CDN/image URLs first; live famous-site screenshots when needed
3. **Hand refs to Design** — borrow/ignore + light tweak (`visual_feedback(purpose=inspiration)`)
4. Downstream implement / consistency / browser proof — out of scope here except interfaces

Agents do not invent great UI; **copy-adapt** must be cheap, broad, and reliable.

---

## R1 — Source taxonomy and planner policy

**Code:** `src/navigation/inspiration_intelligence/planning/source_planner.py`

### Intent class → channels

| Intent class | Gallery query hints | Famous-site categories | Prefer providers |
|--------------|---------------------|------------------------|------------------|
| landing / marketing / saas | saas landing, marketing hero | marketing | onepagelove, lapa, behance, httpster |
| dashboard / admin | admin/analytics dashboard | dashboard | behance, dribbble, siteinspire |
| ecommerce / checkout | storefront, checkout form | ecommerce (+ auth for checkout) | behance, onepagelove, awwwards |
| docs | documentation / developer docs | docs | siteinspire, onepagelove |
| auth / onboarding | login / signup / onboarding | auth (+ marketing) | behance, dribbble, onepagelove |
| mobile | mobile app ui | marketing | dribbble, behance |
| default | seed query only | marketing | FAST_HTTP set |

### Mode → budgets

| Mode | Providers | Famous sites | HTTP workers | Browser workers | Budget |
|------|-----------|--------------|--------------|-----------------|--------|
| **fast** | FAST_HTTP only | ≤2 | 5 | 0 | discover &lt;3s p50; collect &lt;15s p50 |
| **broad** | IMAGE_FIRST (HTTP + limited WAF) | ≤4 | 5 | 1 | slower OK |
| **deep** | full DEFAULT_PROVIDER_PRIORITY | ≤4 | 5 | 2 | research / explicit |

### Stop rules

- Usable pack = **min 3 / target 5** refs with viewable `preview_url` / blob
- Dedupe on candidate_id + normalized preview URL
- **Early cancel** pending HTTP tasks when enough image refs exist

---

## R2 — Gallery image-URL reliability matrix

Sources: provider docs under `src/navigation/inspiration_intelligence/docs/providers/`, anti-bot notes, code paths (`gallery_parse.py`, extract scripts), PERFORMANCE_REVIEW (collect historically 10–60s serial).

| Provider | Tier | Fastest path to design image | HTTP parse | WAF / bot | Median latency (est.) | Recommendation |
|----------|------|------------------------------|------------|-----------|------------------------|----------------|
| **onepagelove** | **fast** | CDN `assets.onepagelove.com/cdn-cgi/image/...` | High | Low | ~0.5–2s | Stay in fast |
| **lapa** | **fast** | Listing/card image URLs via HTTP | High | Low | ~0.5–2s | Stay in fast |
| **behance** | **fast** | Project cover / CDN preview via HTTP adapter | Medium–High | Moderate Adobe CDN | ~1–3s | Stay in fast |
| **httpster** | **fast** | Gallery card images HTTP | High | Low | ~0.5–2s | Stay in fast |
| **siteinspire** | **fast** | Thumb / card images HTTP | Medium | Low | ~1–3s | Stay in fast; deepen selectors |
| **dribbble** | **deep** | Browser + `cdn.dribbble.com` / og:image; cookie helps | **Fails** (202 WAF stub ~2KB) | AWS WAF | ~8–25s headed | Deep / broad only |
| **awwwards** | **deep** | Browser extract thumbs | Unreliable alone | Cookie banner | ~6–20s | Broad/deep |
| **godly** (recent.design) | **deep** | Browser SPA extract | Poor | SPA hydration | ~7–20s | Deep only |
| **land-book** | **drop / pin** | Browser; og often generic | Poor | Slow load-more | ~10–30s | Explicit pin only — not default |

**Spike instrumentation:** collect manifests now emit `provider_ms[]` and `collect_ms` for live measurement.

**Baseline (pre-concurrency, from PERFORMANCE_REVIEW + serial collect):** often **10–60s** for a usable pack when cascading multiple providers + blob materialize.

**Post-spike (mock concurrent wave):** HTTP providers that previously ran serially now overlap; wall time ≈ max(provider) + capture/blob, not sum — path to **&lt;15s p50** on fast path when 1–2 HTTP providers return CDN URLs quickly and early-cancel drops the rest.

---

## R3 — Live famous-site screenshot channel

**Corpus:** `src/navigation/inspiration_intelligence/data/famous_sites_corpus.json`  
**Loader / hit sketch:** `famous_sites.py`

### Design decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Browser owner | Inspiration’s own Chromium on **exclusive queue** (1–2) | Avoid fighting Perception `session_id` browser; anti-bot isolation |
| URL source | Curated corpus by category (not free-form crawl) | Safety, ToS, latency; planner picks categories |
| Capture | **Viewport** default (full-page optional later) | Faster; enough for hero/chrome direction |
| Manifest | `source_kind: live_site` | Distinct from `gallery_image` |

### Hit shape (channel B)

```json
{
  "source_kind": "live_site",
  "provider_id": "famous_site",
  "candidate_id": "live_site:stripe",
  "title": "Stripe",
  "url": "https://stripe.com",
  "screenshot_blob": "…",
  "capture": "viewport",
  "category": "marketing"
}
```

**Build follow-on:** wire `select_famous_sites` into collect when mode ≠ fast-only-galleries and channel list includes `live_site` (corpus + loader shipped; navigate/capture loop is next build phase).

---

## R4 — Concurrency spike results

**Implemented:**

- `concurrent.py` — tier split (HTTP vs browser-heavy)
- `discovery/concurrent_wave.py` — `asyncio` fan-out + early cancel
- `collect.py` — concurrent wave per progressive query; `provider_ms` / `collect_ms`
- `discovery/inspiration.py` — same wave for scout

| Pool | Workers | Work |
|------|---------|------|
| HTTP | 4–8 (default 5) | Gallery list + image URL extract |
| Browser | 1–2 exclusive | WAF galleries + future live-site shots |
| Blob | existing store | Materialize after URL win (parallelize further in next build) |

**Measured (unit spike with delayed mocks):** 3 HTTP providers @ ~200ms each → wall ≈ **~200–250ms** (parallel) vs ~600ms serial; early cancel stops siblings when target refs met.

**Live p50/p95:** run collect with `INSPIRATION_FAST=1` against real HTTP providers and read `collect_ms` / `provider_ms` in the manifest. Research exit criterion: architecture shows clear path to &lt;15s; live harness is Phase 2 build item #6 in parent plan.

---

## R5 — Tool UX (discover vs collect)

| Tool | Role | Latency target |
|------|------|----------------|
| `perception_inspiration_discover` | Concurrent **scout** — URLs + scores, **no blobs** | &lt;3s p50 |
| `perception_inspiration_collect` | Concurrent **acquire** — blobs + seed Spec | &lt;15s p50 fast |

**Double-cascade fix (shipped):**

- Discover mints `discover_token` (scout cache, 30m TTL)
- Collect accepts `discover_token` and/or `candidate_urls` → materialize without re-querying galleries
- Advisory text tells agents to pass the token

---

## R6 — Handoff to Design intelligence

**Locked contract:**

1. Usable pack (3–5 hits with `preview_url` / `inspiration_blob`, optional `live_site` shots)
2. `visual_feedback(purpose=inspiration)` → borrow / ignore = **direction paid**
3. Soft seed Spec via `compile_inspiration_seed_spec` remains follow-on hardening, not a blocker for concurrency

---

## Anti-bot / ToS notes

See `src/navigation/inspiration_intelligence/docs/ANTI_BOT_STRATEGY.md`.

- Never fan out headed Chromium across WAF sites
- Per-provider rate budgets + shared cooldown remain
- No Google SERP scraping in v1
- Famous sites: polite viewport capture, curated allowlist only

---

## Research exit checklist

- [x] Measured baseline narrative + proposed architecture with budgets  
- [x] Clear provider tier list (fast vs deep vs drop)  
- [x] Live-site channel design + corpus + manifest sketch  
- [x] Concurrent HTTP spike with early cancel + timing traces  
- [x] Discover→collect reuse contract  
- [x] Explicit handoff to design extract loop  

---

## Next build phases (after this research)

1. Harden live-site navigate/capture into collect when planner requests `live_site`
2. Parallel blob materialize pool
3. Live p50/p95 harness writing to evals
4. Coordination unpaid inspiration-first (parent Phase 1) once fast path is sticky for agents
