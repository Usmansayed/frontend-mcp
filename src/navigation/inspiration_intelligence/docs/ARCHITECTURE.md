# Inspiration Intelligence — Architecture

Public design inspiration orchestration. **Figma Intelligence** is a separate future module for the user's own Figma account.

## Flow

```text
Agent
  → Intent
  → Search Planner
  → Community Intelligence (query expansion)
  → Provider Manager (priority cascade + early stop)
  → One Page Love | Behance | (optional) Dribbble | Awwwards | SiteInspire | Godly | Land-book
  → Candidate Intelligence
  → Ranking
  → Selection Planner
  → Browser Intelligence (execution only)
  → Design Snapshot → Design Sense → Consistency → Reference Registry
  → Agent
```

## Provider priority

**Fast mode (default, `INSPIRATION_FAST=1`):** One Page Love → Behance only (HTTP/CDN; no Chromium).

**Deep mode (`INSPIRATION_FAST=0` or explicit provider preference):**

Search stops as soon as enough high-confidence candidates are found (default: 2–3 at score ≥ 0.55).

1. One Page Love — HTTP reliable CDN previews
2. Behance — HTTP/CDN
3. Dribbble — WAF; headed browser when needed
4. Awwwards — browser/cookie often required
5. SiteInspire — HTTP then browser
6. Godly — SPA hydration
7. Land-book — browser-required; last resort

## Separation from Figma Intelligence

| Module | Responsibility |
|--------|----------------|
| **Inspiration Intelligence** | Public inspiration sites, screenshots, reference patterns |
| **Figma Intelligence** | User Figma account, files, variables, Community duplication |

Browser automation is an **execution layer** only. Ranking, comparison, and evaluation stay in intelligence modules.

See `docs/providers/` for per-site navigation research.
