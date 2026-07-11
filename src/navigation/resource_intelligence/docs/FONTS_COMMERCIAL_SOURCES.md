# Free Commercial Font Sources

**Policy:** Resource Intelligence **defaults to commercial-use-only** providers. Fonts below are confirmed free for commercial use (Jul 2026 — revalidate before adapters ship).

---

## Tier 0 — Implement first

| Source | License | Self-host | Notes |
|--------|---------|-----------|-------|
| **[Fontsource](https://fontsource.org)** ⭐ | OFL-1.1 / Apache-2.0 / UFL | npm `@fontsource/*` | **Primary path.** 1500+ families, version-locked, mirrors Google Fonts |
| **[Google Fonts](https://fonts.google.com/about)** (via Fontsource) | OFL / Apache | npm via Fontsource | Do not hotlink `fonts.googleapis.com` in production — use Fontsource |
| **[Bunny Fonts](https://fonts.bunny.net)** | OFL (same families as Google) | CSS API or download | GDPR-friendly CDN; commercial per OFL |
| **[Fontshare](https://www.fontshare.com)** | ITF FFL + OFL | CSS API + ZIP | 100+ quality families; free commercial; no font resale |

---

## Tier 1 — Secondary

| Source | License | Notes |
|--------|---------|-------|
| **[Font Squirrel](https://www.fontsquirrel.com)** | Pre-screened commercial | Only “100% Free for Commercial Use” tag |
| **[League of Movable Type](https://www.theleagueofmoveabletype.com)** | OFL | Curated open fonts |
| **[Open Foundry](https://open-foundry.com)** | OFL (per font) | Verify each family page |

---

## License types (all commercial-OK)

| SPDX | Commercial | Attribution in UI |
|------|------------|-------------------|
| **OFL-1.1** | Yes | No (keep license in source) |
| **Apache-2.0** | Yes | No |
| **UFL** (Ubuntu) | Yes | No |
| **ITF FFL** (Fontshare) | Yes | No |

---

## Excluded from default font catalog

| Source | Reason |
|--------|--------|
| **Adobe Fonts** | Subscription — not free |
| **Monotype / commercial foundries** | Paid licenses |
| **Random “free font” blogs** | Unverified license |
| **CC-BY-NC fonts** | Non-commercial only |

---

## Agent guidance

1. **Default:** `perception_font_search` → Fontsource → Bunny → Fontshare
2. **Prefer self-host:** `@fontsource/inter`, `@fontsource/roboto-flex`
3. **Never assume** a font is commercial — read package `LICENSE` or family metadata
4. Set `commercial_required=true` (default) — non-OFL fonts are filtered out

---

## Module wiring

```text
font search plan:
  fontsource → bunny-fonts → fontshare → font-squirrel (commercial filter)
```

Seed data: `graph/seed.py`  
Policy: `license/policy.py` (`commercial_use_denied` gate)
