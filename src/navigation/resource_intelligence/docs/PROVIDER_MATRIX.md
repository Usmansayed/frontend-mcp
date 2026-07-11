# Resource Intelligence — Provider Comparison Matrix

**Revalidated:** Jul 2026 (official docs + GitHub). Re-check before adapter implementation.

## Default policy: commercial-only

Resource Intelligence **does not include** providers in the default catalog unless **commercial use is confirmed** (`commercial_use=true`, `excluded=false`).

**Removed from default:** providers with `commercial_use=false` only (e.g. Humaaans until verified).

**Stays in catalog despite automation bans:** unDraw, Storyset — commercial allowed; `api_automation_allowed=false` is an adapter warning, not exclusion.

**Per-asset filter:** SVG Repo, LottieFiles — skip CC-BY-NC / NC community assets at adapter time.

**Legend**

| Column | Meaning |
|--------|---------|
| Tier | 0 = implement first, 1 = second wave, 2 = later, X = excluded |
| API | Official programmatic search/download |
| Self-host | npm/git/Docker mirror without provider CDN |
| Comm. | Commercial use allowed (typical case) |
| Attr. | Attribution required |
| MCP↓ | Safe for MCP to fetch preview/download on behalf of agent |
| AI | AI training / dataset use allowed |
| Auto | Automated scraping/API orchestration allowed |

---

## Icons

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **Iconify** ⭐ | 0 | Yes | Yes | MIT (API); per-set | Yes | No* | Yes | Yes | Yes | Resolve license per icon collection |
| **Lucide** | 0 | No | Yes (npm) | ISC | Yes | No | Yes | Yes | Yes | 1500+ icons; official React/Vue |
| **Heroicons** | 0 | No | Yes (npm) | MIT | Yes | No | Yes | Yes | Yes | Tailwind ecosystem |
| **Tabler Icons** | 1 | No | Yes (npm) | MIT | Yes | No | Yes | Yes | Yes | 5000+ icons |
| **Phosphor** | 1 | No | Yes (npm) | MIT | Yes | No | Yes | Yes | Yes | Weight variants |
| **Remix Icon** | 1 | No | Yes (npm) | Apache 2.0 | Yes | No | Yes | Yes | Yes | |
| **Material Icons** | 1 | Via Iconify | Yes | Apache 2.0 | Yes | Rec. | Yes | Yes | Yes | Prefer Iconify aggregation |

\*Iconify: no attribution for most sets; check per collection.

---

## Illustrations

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **Open Doodles** ⭐ | 0 | No | Yes (git) | CC0 | Yes | No | Yes | Yes | Yes | Open design; no API |
| **IRA Design** ⭐ | 1 | No | Yes | MIT | Yes | No | Yes | Yes | Yes | |
| **Storyset** | 1 | No | No | Custom | Yes | Yes | Yes* | ? | **No** | *Commercial; automation prohibited — in catalog |
| **unDraw** | 1 | No | No | Custom | Yes | No | Yes* | **No** | **No** | *Commercial; automation + AI prohibited — in catalog |
| **Humaaans** | X | No | Yes | Unverified | **No** | No | **No** | ? | ? | **Excluded — not commercial-confirmed** |

---

## Graphics / SVG

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **SVG Repo** | 1 | svgapi.com | Partial | **Per asset** | Yes* | Varies | Yes* | Varies | Yes | *Commercial assets; skip CC-BY-NC per page |
| **theSVG** | 2 | TBD | No | Free | Yes | No | Caution | ? | TBD | Brand logos; verify ToS |

---

## 3D

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **3dicons** ⭐ | 1 | No | Yes | CC0 | Yes | No | Yes | Yes | Yes | glTF/PNG packs |
| **Poly Pizza** ⭐ | 0 | Yes | No | CC0 / CC-BY | Yes | Per model | Yes | Caution | Yes | API key; check each model license |
| **Khagwal 3D** | 2 | No | Yes | CC0 | Yes | No | Yes | Yes | Yes | Static packs |
| **Poly Haven** | 1 | Yes* | Yes | CC0 assets | Yes | No | Yes** | Caution | **API NC*** | Assets CC0; **API commercial needs license** |

\*API free non-commercial; contact for commercial API.  
\*\*Direct CC0 download OK; API orchestration follows API ToS.

---

## Mockups

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **Mockup Factory** ⭐ | 2 | TBD | Partial | Verify | Verify | ? | TBD | ? | TBD | Research Figma/plugin export path |

---

## Avatars

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **DiceBear** ⭐ | 0 | Yes | Yes (Docker) | MIT + per-style | Yes | Per style | Yes | Yes | Yes* | *Public API non-commercial; commercial self-host |
| **Open Peeps** | 1 | No | Yes | CC0 | Yes | No | Yes | Yes | Yes | Modular SVG |
| **Notion Avatar** | 2 | No | No | Custom | ? | ? | Manual | ? | No | Generator only |

---

## Patterns & Gradients

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **uiGradients** ⭐ | 1 | No | Yes (JSON) | MIT | Yes | No | Yes | Yes | Yes | CSS gradient strings |
| **Hero Patterns** | 1 | No | Yes | MIT | Yes | No | Yes | Yes | Yes | SVG patterns |
| **Pattern Monster** | 2 | No | No | Verify | Verify | ? | TBD | ? | TBD | |

---

## Animations

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **LottieFiles** ⭐ | 1 | Yes | Partial | Lottie Simple | Yes | Encouraged | Yes | Caution | Yes | No competing service clone |
| **Rive** ⭐ | 2 | Editor | Yes (runtime) | MIT runtime | Yes | No | Link only | Yes | N/A | **.riv export requires paid plan**; runtime MIT |

---

## Logos

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **Simple Icons** ⭐ | 0 | No | Yes (npm) | CC0 | Yes* | No | Yes | Yes | Yes | *Trademark caveat per brand |
| **theSVG** ⭐ | 2 | TBD | No | Free | Yes | No | TBD | ? | TBD | Full-color brand SVGs |

---

## Fonts (free commercial — default catalog)

| Provider | Tier | API | Self-host | License | Comm. | Notes |
|----------|------|-----|-----------|---------|-------|-------|
| **Fontsource** ⭐ | 0 | No | Yes (npm) | OFL / Apache / UFL | Yes | **Primary** — 1500+ families, Google mirror |
| **Google Fonts** ⭐ | 0 | Via Fontsource | Yes | OFL / Apache | Yes | Use Fontsource npm, not CDN |
| **Bunny Fonts** ⭐ | 0 | Yes | Yes | OFL | Yes | GDPR-friendly Google mirror |
| **Fontshare** ⭐ | 0 | Yes | Yes | ITF FFL + OFL | Yes | 100+ families; free commercial |
| **Font Squirrel** | 1 | No | Yes | Pre-screened | Yes | “100% free commercial” tag only |

See `FONTS_COMMERCIAL_SOURCES.md`.

---

## Photos

| Provider | Tier | API | Self-host | License | Comm. | Attr. | MCP↓ | AI | Auto | Notes |
|----------|------|-----|-----------|---------|-------|-------|------|----|------|-------|
| **Pexels** ⭐ | 0 | Yes | No | Pexels License | Yes | No† | Yes | Caution | Yes | †API requires prominent Pexels link |
| **Pixabay** | 1 | Yes | No | Pixabay License | Yes | No | Yes | Caution | Yes | API key; verify current terms |
| **Unsplash** | 1 | Yes | No | Unsplash License | Yes | **API yes** | Yes | Caution | Yes | Commercial; API attribution required |

---

## Priority implementation order

**P0 (Core launch):** Iconify, Lucide, Heroicons, Fontsource, Bunny Fonts, Fontshare, DiceBear (self-host), Open Doodles, Pexels, Simple Icons

**P1:** Tabler, Phosphor, Remix, Font Squirrel, IRA Design, Open Peeps, Poly Pizza, uiGradients, Pixabay

**P2:** 3dicons, Mockup Factory, theSVG, Pattern Monster (verify commercial first)

**Excluded from default:** Humaaans (commercial not confirmed)

**Adapter warnings (still commercial):** unDraw, Storyset (automation), SVG Repo / LottieFiles (per-asset NC filter), DiceBear (self-host for commercial API)

---

## Official sources

| Provider | License / API URL |
|----------|-------------------|
| Iconify | https://iconify.design/docs/api/ |
| unDraw | https://undraw.co/license |
| Pexels | https://www.pexels.com/api/documentation/ |
| Unsplash | https://unsplash.com/api-terms |
| DiceBear | https://www.dicebear.com/licenses/ |
| Fontsource | https://fontsource.org |
| Bunny Fonts | https://fonts.bunny.net/faq |
| Fontshare | https://www.fontshare.com/licenses/itf-ffl |
| Font Squirrel | https://www.fontsquirrel.com/faq |
| Google Fonts | https://fonts.google.com/about |
| Simple Icons | https://github.com/simple-icons/simple-icons |
| SVG Repo | https://www.svgrepo.com/page/licensing |
| Poly Pizza | https://poly.pizza/docs/api/v1.1 |
| Poly Haven | https://polyhaven.com/our-api |
| LottieFiles | https://lottiefiles.com/page/license |
| Rive | https://rive.app/docs/runtimes/getting-started |
| Storyset | https://storyset.com/terms |
