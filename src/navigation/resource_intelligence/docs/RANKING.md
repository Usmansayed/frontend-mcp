# Resource Intelligence — Ranking

Ranking selects the best assets after provider search and license filtering.

---

## Inputs

- `ResourceAssetRef` candidates (with provider metadata)
- `ResourceDiscoveryRequest` (prefer_svg, commercial_required, categories)
- Optional **Consistency Intelligence** hints (color tokens, typography, border-radius)
- Optional **Framework Intelligence** (detected stack — prefer Lucide if already in package.json)

---

## Score components (0.0 – 1.0)

| Signal | Weight | Notes |
|--------|--------|-------|
| `relevance` | 0.35 | Query/tag match, collection match |
| `license_permissiveness` | 0.20 | CC0/MIT > CC-BY > Custom |
| `quality` | 0.15 | Provider reputation, vector vs raster |
| `self_hostable` | 0.10 | npm/git > hotlink-only |
| `framework_fit` | 0.10 | Already in project deps |
| `design_system_fit` | 0.10 | Consistency graph alignment |
| `freshness` | 0.05 | Recently updated assets |

---

## Category-specific boosts

| Category | Boost |
|----------|-------|
| Icons | SVG > PNG; prefer sets already in stack (Lucide if `lucide-react` detected) |
| Fonts | Fontsource OFL families matching project mood |
| Photos | Higher resolution + Pexels/Unsplash API compliance |
| Logos | Simple Icons monochrome for dev tools; warn on trademark |
| Avatars | Deterministic seed (DiceBear) for consistent UI |
| 3D | CC0 > CC-BY; prefer glTF |

---

## Penalties

- `attribution_required` when user set `attribution_ok=false` → exclude
- `license_unknown` → heavy penalty or exclude for commercial
- Duplicate assets across providers → merge, keep highest license clarity
- Raster icon when `prefer_svg=true` → penalty

---

## Output

```python
@dataclass
class RankedResource:
    asset: ResourceAssetRef
    overall_score: float
    rationale: str
    degraded: list[str]
```

Top N returned in `ResourceRecommendation.assets` sorted by `overall_score`.

---

## Deduping

Merge key: normalized title + category + perceptual hash (photos) or SVG path hash (icons).

Prefer provider with clearer license when duplicates exist.
