# Component / section pattern inspiration — R&D

**Date:** 2026-07-27  
**Goal:** Fast + reliable inspiration for navbar, footer, modal, button, hero — not only full landing pages.

## Spike results (live HTTP)

| Source | Latency | Usable thumbs | Role |
|--------|---------|---------------|------|
| **navbar.gallery** | ~0.4–0.9s | Many Webflow CDN screenshots | Best for nav |
| **footer.design** | ~0.07–0.5s | Many Webflow CDN screenshots | Best for footers |
| **daisyUI** `img.daisyui.com/images/components/{slug}.webp` | ~0ms (direct URL) | 1 per component | Chrome / controls |
| hero.gallery | ~1s | Few (Framer SPA) | Weak static yield |
| Collect UI | SPA | Poor HTTP | Skip for fast path |
| uiverse.io | 403 CF | None | Skip |
| Landing galleries (OPL) | Fast | **Wrong grain** | Page-only |

Fonts: **not** gallery collect — route to `perception_resource_font_search` (Resource Intelligence).

## Design shipped

```text
component/section/chrome query
  → pattern_acquire (specialists + daisy CDN)   # first, <~1–2s
  → if pack relevant enough: stop
  → else: existing HTTP galleries + multi-scout
font query
  → return font_route hint, skip gallery cascade
```

Code:

- `data/pattern_inspiration_sources.json`
- `pattern_acquire.py`
- Wired in `collect.py` before page galleries

## Agent usage

```text
collect({ query: "navbar with mega menu", inspiration_level: "standard" })
collect({ query: "site footer", inspiration_level: "light" })
collect({ query: "primary button", inspiration_level: "light" })
# fonts:
collect({ query: "serif display font" })  # → resource_font_search hint
```

## Still open

1. More specialist galleries (pricing, sidebar) when HTTP-stable CDNs exist  
2. Optional HEAD validate daisy CDN 404s  
3. HyperUI / Tailgrids HTML parse when they expose static thumbs  
4. Screenshot crop of live famous sites’ headers for nav (slower, max level only)

## Reliability fixes (same day)

| Bug | Fix |
|-----|-----|
| Font route still returned multi_scout junk | `need_scout` / cascade honor `skip_cascade`; font returns 0 hits + route |
| Modal (component) + 1 daisy still fell through to OPL | `_pack_ready`: ≥1 pattern CDN/gallery hit stops chrome/component |
| Pattern soft-stop then wide `force_variety` scout | `skip_cascade` also for `enough_relevant_refs_pattern` |
