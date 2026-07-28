# Web search + live visual inspiration — R&D

**Date:** 2026-07-27  
**Goal:** Inspiration as a **search + visual** engine — not 0–1 daisy cards.

## Problem

Pattern soft-stop at ≥1 CDN hit + daisy single-slug packs returned **1 or 0** visuals.
Live screenshots existed only for curated famous sites on `max`. No open-web search.

## Design (Channel C)

```text
query
  → pattern CDN/galleries (fast)
  → if pack thin: DuckDuckGo HTML search
       → concurrent OG image fetch (many visual thumbs, no browser)
       → optional viewport screenshots of top result pages (wide/max)
  → galleries / multi-scout / famous sites as before
```

| Piece | Role |
|-------|------|
| `web_search.py` | DuckDuckGo HTML → organic URLs (no API key) |
| `web_inspire.py` | Search → OG wave → screenshot wave |
| `levels.py` | standard: web+OG; wide: +2 SS; max: +4 SS + famous |
| Soft-stop | chrome/component needs ≥3–4 pattern/web visuals, not 1 |

## Agent knobs

```text
inspiration_level: standard | wide | max
include_web_search: true|false   # default from level
max_web_screenshots: N           # override
allow_browser_screenshot: true   # bumps screenshots to ≥2
```

Fonts still route to Resource Intelligence (0 gallery hits by design).

## Not doing (yet)

- Google SERP scrape (policy)
- DDG image JSON (vqd fragile in spike)

## Optional paid search (shipped)

`search_web()` tries `SERPER_API_KEY` then `BRAVE_API_KEY`, else DuckDuckGo HTML.
