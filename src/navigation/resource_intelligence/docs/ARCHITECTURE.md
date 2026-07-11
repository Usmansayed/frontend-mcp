# Resource Intelligence — Architecture

**Status:** Research & Architecture v1 (Jul 2026)  
**Module path:** `src/navigation/resource_intelligence/`

Resource Intelligence is the **orchestration and intelligence engine** for production-ready creative assets. It is not a storage layer, CDN, or asset host.

---

## Mission

When an agent needs icons, illustrations, photos, fonts, logos, avatars, 3D assets, mockups, animations, gradients, or patterns — it asks Resource Intelligence.

The module decides:

- Which **categories** apply to the query
- Which **providers** to search (priority, license, API budget)
- Whether **licenses** allow the intended use
- Which asset **best matches** the design system (via Consistency Intelligence hooks)
- How to return **access URLs** without permanently hosting copyrighted files

---

## Philosophy

Same pattern as Component Intelligence and Inspiration Intelligence:

```text
Agent
  → Intent / Query Parser
  → Resource Planner (categories, providers, budget)
  → Provider Manager (parallel search, early stop)
  → Provider Adapters (Iconify, Pexels, Fontsource, …)
  → License Intelligence (filter + annotate)
  → Ranking (quality, license, design-system fit)
  → Recommendation
  → Agent
```

**Hard rules:**

1. MCP never permanently stores or redistributes third-party asset packs.
2. Every result carries structured **LicenseProfile** metadata.
3. **Default catalog is commercial-only** — exclude providers only when `commercial_use=false` (not for automation/attribution bans alone).
4. **Automation / AI restrictions** are flagged on `LicenseProfile` (`api_automation_allowed`, `ai_training_allowed`) — advisory at adapter time, not catalog exclusion.
5. **Per-asset** licenses override provider defaults (Iconify collections, SVG Repo CC-BY-NC, Poly Pizza CC-BY).
6. Revalidate official license pages before shipping adapters — licenses change.

See `FONTS_COMMERCIAL_SOURCES.md` for free commercial font ecosystems.

---

## Subsystems

| Subsystem | Doc | Responsibility |
|-----------|-----|----------------|
| Resource Graph | `RESOURCE_GRAPH_SCHEMA.md` | Provider + asset metadata knowledge |
| License Intelligence | `LICENSE_INTELLIGENCE.md` | SPDX classification, compliance gates |
| Planning | `PLANNING.md` | Category detection, provider routing, budget |
| Providers | `PROVIDER_MATRIX.md` + `providers/` | Per-ecosystem adapters |
| Ranking | `RANKING.md` | Score and dedupe candidates |
| MCP | `MCP_TOOLS.md` | `perception_resource_*` tool surface |

---

## Categories

| Category | Primary providers (tier 0) |
|----------|---------------------------|
| Icons | Iconify, Lucide, Heroicons, Tabler, Phosphor |
| Illustrations | Open Doodles, IRA Design, ManyPixels |
| Graphics / SVG | SVG Repo |
| 3D | 3dicons, Poly Pizza, Poly Haven |
| Mockups | Mockup Factory |
| Avatars | DiceBear, Open Peeps |
| Patterns / Gradients | uiGradients, Hero Patterns |
| Animations | LottieFiles, Rive (runtime) |
| Logos | Simple Icons, theSVG |
| Fonts | Fontsource, Bunny Fonts, Fontshare, Google Fonts (via Fontsource) |
| Photos | Pexels, Pixabay, Unsplash |

See `PROVIDER_MATRIX.md` for full comparison.

---

## Excluded providers (non-commercial only)

| Provider | Reason |
|----------|--------|
| **Humaaans** | Commercial license not SPDX-confirmed |

## Commercial but restricted (stay in catalog — adapter flags)

| Provider | Restriction |
|----------|-------------|
| **unDraw** | No automation / AI training |
| **Storyset** | No scraping; attribution on free tier |
| **SVG Repo** | Skip CC-BY-NC assets per page |
| **Poly Haven** | CC0 assets commercial; API ToS limits commercial API |
| **DiceBear** | Public API non-commercial — self-host for commercial |

Agents may still **link** users to manual download on excluded sites; MCP adapters must not automate them.

---

## Cross-module integration

```text
Resource Intelligence
  ← Framework Intelligence     (npm/font packages, React icon libs)
  ← Consistency Intelligence   (token colors, typography for font/icon fit)
  ← Component Intelligence     (shadcn/Lucide already in stack — avoid duplicate icon search)
  ← Inspiration Intelligence   (page-level mood → illustration style hints)
```

**Boundary with Component Intelligence:** Components are installable UI building blocks. Resources are discrete assets (SVG path, font file, photo URL). Component search may *reference* Iconify/Lucide but Resource Intelligence owns standalone asset discovery.

---

## Data flow (recommended asset ref)

Agents receive `ResourceAssetRef`:

- `access_url` — provider URL, npm package, or API link (not MCP-hosted file)
- `preview_url` — optional thumbnail
- `license` — full `LicenseProfile`
- `attribution_text` — preformatted when required (Unsplash API, CC-BY)
- `score` + `metadata` — ranking rationale

Optional **ephemeral preview blobs** (like Inspiration Intelligence) may be added later for vision — same TTL/session pattern, separate from permanent storage.

---

## Implementation phases

See `ROADMAP.md`:

1. **Research** ← current
2. **Core** — models, graph, license engine, planner, registry
3. **Providers** — P0 adapters (Iconify, Lucide, Fontsource, DiceBear, Pexels, Open Doodles, Simple Icons)
4. **Intelligence** — ranking, consistency hooks, attribution builder
5. **MCP Tools** — `perception_resource_search` + category shortcuts

---

## Folder structure

See `FOLDER_STRUCTURE.md`.

---

## Revalidation checklist

Before each provider adapter ships:

1. Official license page (current)
2. API ToS / automation rules
3. Commercial use + attribution
4. Redistribution / competing service clauses
5. AI / dataset restrictions
6. Rate limits + auth
7. Maintenance status (last commit / API changelog)
8. Self-host path (npm, Docker, git mirror)

Document findings in `providers/<id>/LICENSE.md` and update `graph/seed.py`.
