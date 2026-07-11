# Anti-bot & Browser Strategy — Inspiration Intelligence

Inspiration sites are accessed via **browser-based browsing** (Browser Intelligence / `browser_use`), not official third-party APIs where those APIs are not permitted for this use case.

**Dribbble:** The official Dribbble API is **not** used. Discovery and capture rely on headed browser sessions subject to [Dribbble's terms](https://dribbble.com/terms).

## Honest expectations

| Site | Browser (headed) | Session cookie | HTTP fallback |
|------|------------------|----------------|---------------|
| Dribbble | Primary path | Full grid previews when logged in | Metadata only |
| Behance+ | Planned | TBD | Not enabled yet |

**We do not hammer all six sites every run.** Priority cascade + early stop + per-run rate budgets keep footprint low.

## Browser execution

All inspiration site browsing uses the **Perception MCP browser** (`PerceptionBrowserRuntime`):
- `perception_session_start` equivalent via `SessionStore` (headed)
- `perception_navigate_and_observe` via `scan_page`
- `perception_execute_script` via `evaluate_js` for DOM extraction

Set `INSPIRATION_HEADLESS=true` only for CI — default is headed.

```text
1. Browser + DRIBBBLE_SESSION_COOKIE  → logged-in search grid (full previews)
2. Browser (anonymous, headed)        → DOM extraction after hydration
3. HTTP search HTML                   → degraded metadata fallback
4. og:image on shot page              → capture fallback (social preview)
5. Browser screenshot                 → last-resort viewport capture
```

## Environment variables

```bash
# Copy cookie from logged-in browser (DevTools → Application → Cookies → dribbble.com)
DRIBBBLE_SESSION_COOKIE="_dribbble_session=...; ..."

# Global inspiration browser settings
INSPIRATION_HEADLESS=false          # default: headed (less bot flags)
INSPIRATION_RATE_LIMIT_MS=2000      # min spacing between provider requests
```

## Fast mode (default — single search <20s)

`INSPIRATION_FAST=1` (default on) optimizes for the common case: **one search when building a page**.

| Behavior | Fast mode |
|----------|-----------|
| Queries | 1 (seed only) |
| Dribbble | HTTP first (~3s); browser only if session cookie set |
| Fallback | Behance HTTP (~3s) if Dribbble empty |
| Early stop | After 2 high-confidence hits |
| Within-run delay | 0.5–1.5s between requests |
| Cooldown between runs | 30s (`INSPIRATION_MIN_COOLDOWN_S`) |

Disable for deep multi-query research: `INSPIRATION_FAST=0`

## Usage gate (production)

Inspiration runs are **not** for background polling. Repeat runs blocked for **30 seconds** by default (`INSPIRATION_MIN_COOLDOWN_S=30`).

```text
Agent building a page/section → inspiration discover (once)
  → max 3 searches per provider per run
  → ~60s between requests (INSPIRATION_MIN_DELAY_S=60)
  → early stop when enough hits found
```

Cache file: `.cache/inspiration_usage.json`  
Bypass (probes/tests only): `INSPIRATION_FORCE=1`

## Anti-bot policies (built-in)

- **Jittered delays** between requests (2–6s per provider)
- **Per-run request budget** (default 6 calls per provider)
- **Block detection** — 403/429, WAF, CAPTCHA keywords → degrade + fall through
- **Headed browser default** for Dribbble
- **Early stop** — don't query lower-priority providers when enough hits found

## Dribbble login-gated images

Dribbble shows full grid images to logged-in users only. Workarounds (browser-only):

1. **Set `DRIBBBLE_SESSION_COOKIE`** — browser session sees the same grid as your account
2. **og:image extraction** — shot detail pages expose Open Graph images for sharing
3. **Viewport screenshot** — capture shot page via browser when preview URL unavailable

## What we store

Only **navigation knowledge** (selectors, URLs, timing) — not copyrighted page dumps or permanent screenshot datasets.

## What we do not use

- Dribbble API v2 for inspiration search or image retrieval
- Bulk scraping without rate limits or session context
