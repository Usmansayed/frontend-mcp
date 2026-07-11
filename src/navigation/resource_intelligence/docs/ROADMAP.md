# Resource Intelligence — Roadmap

## Phase 0 — Research & Architecture ✅ (Jul 2026)

- [x] Provider comparison matrix (`PROVIDER_MATRIX.md`)
- [x] Resource Graph schema (`RESOURCE_GRAPH_SCHEMA.md`)
- [x] License Intelligence architecture
- [x] Ranking + Planning architecture
- [x] MCP tool specification
- [x] Module folder scaffold + seed graph
- [x] Exclusion policy — **commercial_use=false only** (automation bans stay in catalog)
- [ ] Per-provider `providers/<id>/LICENSE.md` deep dives (P0 only)

---

## Phase 1 — Core

- [ ] `providers/protocol.py` — `ResourceProvider` interface
- [ ] `intent/parser.py` — query → categories
- [ ] `planning/search_planner.py` + `planning/orchestrator.py`
- [ ] `license/resolver.py` + `license/policy.py` + `license/exclusions.py`
- [ ] `graph/store.py` — load/save graph, TTL asset cache
- [ ] `ranking/ranker.py`
- [ ] `search/executor.py` — parallel provider execution
- [ ] `service.search()` implementation
- [ ] Unit tests: license gates, planner, ranker

---

## Phase 2 — P0 Providers

| Provider | Adapter | Notes |
|----------|---------|-------|
| Iconify | `providers/iconify/` | Collection license resolver |
| Lucide | `providers/lucide/` | npm metadata + SVG paths |
| Fontsource | `providers/fontsource/` | npm family search |
| DiceBear | `providers/dicebear/` | Self-host Docker path |
| Open Doodles | `providers/open_doodles/` | Static manifest |
| Pexels | `providers/pexels/` | API key + attribution |
| Simple Icons | `providers/simple_icons/` | npm slug search |

---

## Phase 3 — Intelligence

- [ ] Consistency Intelligence hook (font/icon style fit)
- [ ] Framework Intelligence hook (existing deps)
- [ ] Attribution text builder
- [ ] Dedup + merge across providers
- [ ] Component Intelligence boundary (redirect component queries)

---

## Phase 4 — P1 Providers

- Heroicons, Tabler, Phosphor, SVG Repo (per-asset license)
- Poly Pizza, LottieFiles, uiGradients
- Pixabay, Unsplash (API attribution)
- IRA Design, Open Peeps, 3dicons

---

## Phase 5 — MCP Tools

- [ ] `perception_resource_search`
- [ ] Category shortcuts (`perception_icon_search`, …)
- [ ] `perception://resource-guide` resource
- [ ] AGENT_GUIDE §14 playbook
- [ ] Contract tests

---

## Phase 6 — Optional

- [ ] Ephemeral preview blobs (session-scoped)
- [ ] `perception_resource_license_check`
- [ ] Poly Haven direct CC0 links (non-API)
- [ ] Rive metadata (no .riv hosting)
- [ ] Mockup Factory, theSVG, Pattern Monster

---

## Non-goals

- Hosting asset CDN
- Bulk mirroring provider catalogs
- Automating unDraw / Storyset
- AI training datasets from licensed assets
