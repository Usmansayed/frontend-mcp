# Provider tier matrix (Inspiration Intelligence)

**Updated:** 2026-07-26 — see also `docs/research/inspiration-layer-enlargement.md`.

| Provider | Tier | Image-URL path | Notes |
|----------|------|----------------|-------|
| onepagelove | **fast** | CDN `assets.onepagelove.com` | Primary HTTP |
| lapa | **fast** | Card/listing images | HTTP |
| behance | **fast** | Cover CDN | HTTP adapter |
| httpster | **fast** | Gallery cards | HTTP |
| siteinspire | **broad/deep** | Thumbs | Removed from fast (browser-prone) |
| dribbble | **deep** | Browser + cdn/og | WAF blocks plain HTTP |
| awwwards | **broad/deep** | Browser extract | Cookie banner |
| godly | **deep** | Browser SPA | recent.design |
| land-book | **pin only** | Browser | Unreliable previews |

Modes: `fast` → fast tier only; `broad` → + limited browser; `deep` → full cascade.
