# Resource Intelligence — Planning

The planner decides **what to search** before any provider call.

---

## Flow

```text
parse_query(query)
  → detect_categories()        # icon, photo, font, …
  → build_resource_plan()
  → select_providers()         # priority + license + budget
  → schedule_passes()          # parallel vs sequential
  → execute (SearchExecutor)
```

---

## Category detection

Lexicon + intent rules (like Component Intelligence):

| Query signal | Categories |
|--------------|------------|
| "icon", "svg icon", "lucide" | `icon` |
| "illustration", "empty state art" | `illustration` |
| "photo", "stock image", "hero image" | `photo` |
| "font", "typography", "inter" | `font` |
| "logo", "brand mark", "github logo" | `logo` |
| "avatar", "profile picture", "user pic" | `avatar` |
| "gradient", "background gradient" | `gradient` |
| "pattern", "seamless" | `pattern` |
| "lottie", "animation", "loader" | `animation` |
| "3d", "mockup" | `3d`, `mockup` |

Default: infer from nouns; multi-category queries search in parallel.

---

## Provider selection

```text
For each category:
  1. Load ProviderNodes from Resource Graph (tier ascending)
  2. Filter excluded + `commercial_use=false` (default — commercial-only catalog)
  3. Apply provider_preference if set
  4. Cap providers per category (default 3)
  5. Early stop when enough high-confidence hits (score ≥ 0.7)
```

### Priority tables (default)

| Category | Order |
|----------|-------|
| icon | iconify → lucide → heroicons → tabler |
| font | fontsource → bunny-fonts → fontshare → font-squirrel → google-fonts (via fontsource) |
| photo | pexels → pixabay → unsplash |
| avatar | dicebear → open-peeps |
| logo | simple-icons → thesvg |
| illustration | open-doodles → ira-design |
| svg | svg-repo |
| 3d | poly-pizza → 3dicons → poly-haven-direct |

---

## Execution modes

| Mode | When |
|------|------|
| **Parallel** | Independent categories (icon + photo) |
| **Sequential** | Rate-limited APIs (Pexels + Unsplash same burst) |
| **Self-host first** | `prefer_self_hosted=true` → npm/git before HTTP API |
| **Rescue pass** | Primary empty → fallback tier-1 provider |

---

## API budget

```text
INSPIRATION_FAST-style limits for resources:
  RESOURCE_API_BUDGET=12        # max provider calls per request
  RESOURCE_EARLY_STOP=3         # min hits before skip lower priority
  PEXELS_API_KEY=...
  UNSPLASH_ACCESS_KEY=...
  POLY_PIZZA_API_KEY=...
```

Planner records `degraded[]` when budget exhausted.

---

## Plan output

```python
@dataclass
class ResourceSearchPlan:
    seed_query: str
    categories: list[ResourceCategory]
    provider_ids: list[str]
    passes: list[ResourceSearchPass]
    filters: dict[str, Any]
    degraded: list[str]
```

Passed to `SearchExecutor` — mirrors `component_intelligence/search/executor.py` pattern.

---

## Cross-module hints

| Module | Hint |
|--------|------|
| Framework Intelligence | `lucide-react` installed → boost Lucide, skip redundant Iconify |
| Consistency Intelligence | primary font family → Fontsource match |
| Component Intelligence | if query is "button component" → defer to Component Intelligence, not icons |

Planner emits `advisory` when query better suited to another module.
